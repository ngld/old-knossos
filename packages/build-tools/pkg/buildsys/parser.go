package buildsys

import (
	"context"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"runtime"
	"strings"

	"github.com/aidarkhanov/nanoid"
	"github.com/rotisserie/eris"
	"go.starlark.net/starlark"
	"mvdan.cc/sh/v3/expand"
	"mvdan.cc/sh/v3/syntax"
)

// * Helpers

func normalizePath(thread *starlark.Thread, pathList ...string) string {
	result := filepath.Dir(thread.Local("filepath").(string))

	for _, path := range pathList {
		if strings.HasPrefix(path, "//") {
			result = filepath.Join(thread.Local("projectRoot").(string), path[2:])
		} else if strings.HasPrefix(path, "/") {
			result = filepath.Join(filepath.VolumeName(result), path)
		} else if !filepath.IsAbs(path) {
			result = filepath.Join(result, path)
		} else {
			result = path
		}
	}

	return filepath.Clean(result)
}

func simplifyPath(thread *starlark.Thread, path string) string {
	projectRoot := thread.Local("projectRoot").(string)
	absPath, err := filepath.Abs(path)
	if err != nil {
		return path
	}

	if strings.HasPrefix(absPath, projectRoot) {
		return "//" + absPath[len(projectRoot)+1:]
	}
	return path
}

type starlarkIterable interface {
	Len() int
	Iterate() starlark.Iterator
}

func starlarkIterable2stringSlice(input starlarkIterable, field string) ([]string, error) {
	if value, ok := input.(*starlark.List); ok && value == nil {
		return []string{}, nil
	}

	result := make([]string, 0, input.Len())
	iter := input.Iterate()

	var item starlark.Value
	for iter.Next(&item) {
		switch value := item.(type) {
		case starlark.String:
			result = append(result, value.GoString())
		default:
			return nil, eris.Errorf("expected all items in %s to be strings but found %s", field, item.Type())
		}
	}
	return result, nil
}

func shellReadDir(path string) ([]os.FileInfo, error) {
	if path == "" {
		path = "."
	}

	return ioutil.ReadDir(path)
}

func resolvePatternLists(thread *starlark.Thread, base string, patterns []string) ([]string, error) {
	result := []string{}
	cfg := expand.Config{
		ReadDir:  shellReadDir,
		GlobStar: true,
	}

	parser := syntax.NewParser()

	for _, item := range patterns {
		item = normalizePath(thread, base, item)
		item = filepath.ToSlash(item)

		words := make([]*syntax.Word, 0)
		parser.Words(strings.NewReader(item), func(w *syntax.Word) bool {
			words = append(words, w)
			return true
		})

		matches, err := expand.Fields(&cfg, words...)
		if err != nil {
			return nil, eris.Wrapf(err, "Failed to resolve pattern %s", item)
		}

		for _, match := range matches {
			// If a pattern didn't match anything, it's returned as a result. Skip those results.
			if !strings.Contains(match, "*") {
				result = append(result, match)
			}
		}
	}
	return result, nil
}

func processCmdParts(parts starlark.Tuple, parser *syntax.Parser, base string) (*syntax.CallExpr, error) {
	envVars := make([]string, 0, len(parts))
	for _, part := range parts {
		end := false
		switch value := part.(type) {
		case starlark.String:
			if strings.Contains(value.GoString(), "=") {
				envVars = append(envVars, value.GoString())
			} else {
				end = true
			}
		default:
			break
		}

		if end {
			break
		}
	}

	var cmd *syntax.CallExpr
	if len(envVars) > 0 {
		joinedEnvVars := strings.Join(envVars, " ")
		result, err := parser.Parse(strings.NewReader(joinedEnvVars), "env vars")
		if err != nil {
			return nil, eris.Wrapf(err, "failed to parse command vars %s", joinedEnvVars)
		}

		if len(result.Stmts) != 1 || result.Stmts[0].Cmd == nil {
			return nil, eris.Errorf("malformed env vars %s", joinedEnvVars)
		}

		var ok bool
		cmd, ok = result.Stmts[0].Cmd.(*syntax.CallExpr)
		if !ok || cmd.Assigns == nil {
			return nil, eris.Errorf("malformed env vars %s", joinedEnvVars)
		}
	} else {
		cmd = new(syntax.CallExpr)
	}

	argCount := len(parts) - len(envVars)
	cmd.Args = make([]*syntax.Word, argCount)
	for a, arg := range parts[len(envVars):] {
		lit := new(syntax.Lit)
		lit.ValuePos = syntax.Pos{}
		lit.ValueEnd = syntax.Pos{}

		switch value := arg.(type) {
		case starlark.String:
			lit.Value = value.GoString()
		case StarlarkPath:
			lit.Value = string(value)

			if filepath.IsAbs(lit.Value) {
				// absolute paths cause issues on Windows
				var err error
				relValue, err := filepath.Rel(base, lit.Value)
				if err == nil {
					lit.Value = relValue
				}
			}

			lit.Value = filepath.ToSlash(lit.Value)
		default:
			return nil, eris.Errorf("found argument of type %s but only strings and paths are supported: %s", arg.Type(), arg.String())
		}

		cmd.Args[a] = new(syntax.Word)
		cmd.Args[a].Parts = []syntax.WordPart{lit}
	}

	return cmd, nil
}

func warn(thread *starlark.Thread, msg string, args ...interface{}) {
	filepath := thread.Local("filepath").(string)
	ctx := thread.Local("ctx").(context.Context)
	pos := thread.CallFrame(1).Pos

	filepath = simplifyPath(thread, filepath)

	log(ctx).Warn().
		Msgf("%s:%d:%d: "+msg, append([]interface{}{filepath, pos.Line, pos.Col}, args...)...)
}

// * Builtin functions

func resolvePath(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	base := ""

	if len(kwargs) > 0 {
		for _, kv := range kwargs {
			key := kv[0].(starlark.String).GoString()

			if key == "base" {
				switch value := kv[1].(type) {
				case starlark.String:
					base = value.GoString()
				case StarlarkPath:
					base = string(value)
				default:
					return nil, eris.Errorf("invalid type %s for keyword base, expected string or path", kv[1].Type())
				}

				base = normalizePath(thread, base)
			} else {
				return nil, eris.Errorf("unexpected keyword argument %s", key)
			}
		}
	}

	if len(args) < 1 {
		return nil, eris.New("expects at least one argument")
	}

	parts := make([]string, len(args))
	for idx, path := range args {
		switch value := path.(type) {
		case starlark.String:
			parts[idx] = value.GoString()
		default:
			return nil, eris.Errorf("only accepts string arguments but argument %d was a %s", idx, path.Type())
		}
	}

	normPath := normalizePath(thread, parts...)
	if base != "" {
		var err error
		normPath, err = filepath.Rel(base, normPath)
		if err != nil {
			return nil, err
		}
	}

	return StarlarkPath(normPath), nil
}

func option(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var name string
	var defaultValue starlark.Value

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &name, &defaultValue)
	if err != nil {
		return nil, err
	}

	options := thread.Local("options").(map[string]string)
	value, ok := options[name]
	if !ok {
		return defaultValue, nil
	}

	return starlark.String(value), nil
}

func getenv(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var key string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &key)
	if err != nil {
		return nil, err
	}

	envOverrides := thread.Local("envOverrides").(map[string]string)
	value, ok := envOverrides[key]
	if !ok {
		value = os.Getenv(key)
	}

	return starlark.String(value), nil
}

func setenv(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var key string
	var value string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 2, &key, &value)
	if err != nil {
		return nil, err
	}

	envOverrides := thread.Local("envOverrides").(map[string]string)
	envOverrides[key] = value

	return starlark.True, nil
}

func prependPathDir(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var pathDir string

	if len(args) != 1 {
		return nil, eris.New("got %d arguments, want 1")
	}

	switch value := args[0].(type) {
	case starlark.String:
		pathDir = value.GoString()
	case StarlarkPath:
		pathDir = string(value)
	default:
		return nil, eris.Errorf("for parameter 1: got %s, want path or string", args[0].Type())
	}

	envOverrides := thread.Local("envOverrides").(map[string]string)
	path, ok := envOverrides["PATH"]
	if !ok {
		path = os.Getenv("PATH")
	}

	envOverrides["PATH"] = normalizePath(thread, pathDir) + string(os.PathListSeparator) + path

	return starlark.String(envOverrides["PATH"]), nil
}

func task(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var deps *starlark.List
	var skipIfExists *starlark.List
	var inputs *starlark.List
	var outputs *starlark.List
	var env *starlark.Dict
	var cmds *starlark.List

	task := new(Task)

	err := starlark.UnpackArgs(fn.Name(), args, kwargs, "short??", &task.Short, "hidden?", &task.Hidden,
		"desc?", &task.Desc, "deps?", &deps, "base?", &task.Base, "skip_if_exists?", &skipIfExists, "inputs?",
		&inputs, "outputs?", &outputs, "env?", &env, "cmds?", &cmds)
	if err != nil {
		return nil, err
	}

	if task.Short == "" {
		task.Hidden = true
		task.Short = "auto#" + nanoid.New()
	}

	task.Env = map[string]string{}

	if task.Base == "" {
		task.Base = "."
	}
	task.Base = normalizePath(thread, task.Base)

	task.Deps, err = starlarkIterable2stringSlice(deps, "deps")
	if err != nil {
		return nil, err
	}

	skipPatterns, err := starlarkIterable2stringSlice(skipIfExists, "skip_if_exists")
	if err != nil {
		return nil, err
	}

	inputPatterns, err := starlarkIterable2stringSlice(inputs, "inputs")
	if err != nil {
		return nil, err
	}

	outputPatterns, err := starlarkIterable2stringSlice(outputs, "outputs")
	if err != nil {
		return nil, err
	}

	task.SkipIfExists, err = resolvePatternLists(thread, task.Base, skipPatterns)
	if err != nil {
		return nil, err
	}

	task.Inputs, err = resolvePatternLists(thread, task.Base, inputPatterns)
	if err != nil {
		return nil, err
	}

	task.Outputs, err = resolvePatternLists(thread, task.Base, outputPatterns)
	if err != nil {
		return nil, err
	}

	if env != nil {
		for _, rawKey := range env.Keys() {
			var key string

			switch value := rawKey.(type) {
			case starlark.String:
				key = value.GoString()
			default:
				return nil, eris.Errorf("found key type %s in env map but only strings are supported", rawKey.Type())
			}

			rawValue, _, err := env.Get(rawKey)
			if err != nil {
				return nil, err
			}
			switch value := rawValue.(type) {
			case starlark.String:
				task.Env[key] = value.GoString()
			default:
				return nil, eris.Errorf("found value of type %s for key %s but only strings are supported", rawValue.Type(), key)
			}
		}
	}

	parser := syntax.NewParser()
	task.Cmds = make([]interface{}, 0)
	iter := cmds.Iterate()
	var item starlark.Value
	idx := 0
	for iter.Next(&item) {
		switch value := item.(type) {
		case starlark.String:
			reader := strings.NewReader(value.GoString())
			result, err := parser.Parse(reader, fmt.Sprintf("%s:%d", task.Short, idx))
			if err != nil {
				return nil, eris.Wrapf(err, "%s: failed to parse command %s", fn.Name(), value.GoString())
			}

			for _, stmt := range result.Stmts {
				task.Cmds = append(task.Cmds, stmt)
			}
		case starlark.Tuple:
			cmd, err := processCmdParts(value, parser, task.Base)
			if err != nil {
				return nil, err
			}

			task.Cmds = append(task.Cmds, &syntax.Stmt{Cmd: cmd})
		case *starlark.List:
			parts := make(starlark.Tuple, value.Len())
			subIter := value.Iterate()
			var subItem starlark.Value
			subIdx := 0
			for subIter.Next(&subItem) {
				parts[subIdx] = subItem
				subIdx++
			}
			subIter.Done()

			cmd, err := processCmdParts(parts, parser, task.Base)
			if err != nil {
				return nil, err
			}

			task.Cmds = append(task.Cmds, &syntax.Stmt{Cmd: cmd})
		case *Task:
			task.Cmds = append(task.Cmds, value)
		default:
			return nil, eris.Errorf("%s: unexpected type %s. Only strings, tuples and lists are valid", fn.Name(), item.Type())
		}

		idx++
	}
	iter.Done()

	if inputs != nil && inputs.Len() > 0 && (outputs == nil || outputs.Len() == 0) {
		warn(thread, "%s: found inputs but no outputs", fn.Name())
	}

	if !task.Hidden {
		knownTasks := thread.Local("tasks").([]*Task)
		thread.SetLocal("tasks", append(knownTasks, task))
	}
	return task, nil
}

// Parse parses the given file and returns a TaskList which contains all named tasks declared on the global scope
func Parse(ctx context.Context, filename, projectRoot string, options map[string]string) (TaskList, error) {
	projectRoot, err := filepath.Abs(projectRoot)
	if err != nil {
		return nil, err
	}

	filename, err = filepath.Abs(filename)
	if err != nil {
		return nil, err
	}

	builtins := starlark.StringDict{
		"OS":           starlark.String(runtime.GOOS),
		"ARCH":         starlark.String(runtime.GOARCH),
		"resolve_path": starlark.NewBuiltin("resolve_path", resolvePath),
		"option":       starlark.NewBuiltin("option", option),
		"getenv":       starlark.NewBuiltin("getenv", getenv),
		"setenv":       starlark.NewBuiltin("setenv", setenv),
		"prepend_path": starlark.NewBuiltin("prepend_path", prependPathDir),
		"task":         starlark.NewBuiltin("task", task),
	}

	thread := &starlark.Thread{
		Name: "main",
		Print: func(thread *starlark.Thread, msg string) {
			log(ctx).Info().Str("thread", thread.Name).Msg(msg)
		},
	}
	thread.SetLocal("ctx", ctx)
	thread.SetLocal("filepath", filename)
	thread.SetLocal("projectRoot", projectRoot)
	thread.SetLocal("options", options)
	thread.SetLocal("envOverrides", map[string]string{})
	thread.SetLocal("tasks", []*Task{})

	script, err := ioutil.ReadFile(filename)
	if err != nil {
		return nil, eris.Wrapf(err, "failed to read file")
	}

	// wrap the entire script in a function to work around the limitation that ifs are only allowed inside functions
	wrappedScript := "def main():\n    " + strings.ReplaceAll(string(script), "\n", "\n    ") + "\n\nmain()\n"
	_, err = starlark.ExecFile(thread, simplifyPath(thread, filename), wrappedScript, builtins)
	if err != nil {
		if evalError, ok := err.(*starlark.EvalError); ok {
			return nil, eris.Errorf("failed to execute %s:\n%s", simplifyPath(thread, filename), evalError.Backtrace())
		}
		return nil, eris.Wrap(err, "failed to execute")
	}

	envOverrides := thread.Local("envOverrides").(map[string]string)
	tasks := TaskList{}
	for _, task := range thread.Local("tasks").([]*Task) {
		tasks[task.Short] = task

		for name, value := range envOverrides {
			_, present := task.Env[name]
			if !present {
				task.Env[name] = value
			}
		}
	}

	return tasks, nil
}
