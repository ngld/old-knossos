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
	"mvdan.cc/sh/v3/syntax"
)

type parserCtx struct {
	ctx          context.Context
	options      map[string]ScriptOption
	optionValues map[string]string
	envOverrides map[string]string
	yamlCache    map[string]interface{}
	filepath     string
	projectRoot  string
	tasks        []*Task
	initPhase    bool
}

// * Helpers

func getCtx(thread *starlark.Thread) *parserCtx {
	return thread.Local("parserCtx").(*parserCtx)
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
		var encodedValue string

		switch value := arg.(type) {
		case starlark.String:
			encodedValue = value.GoString()
		case StarlarkPath:
			encodedValue = string(value)

			if filepath.IsAbs(encodedValue) {
				// absolute paths cause issues on Windows
				var err error
				relValue, err := filepath.Rel(base, encodedValue)
				if err == nil {
					encodedValue = relValue
				}
			}

			encodedValue = filepath.ToSlash(encodedValue)
		default:
			return nil, eris.Errorf("found argument of type %s but only strings and paths are supported: %s", arg.Type(), arg.String())
		}

		var wordPart syntax.WordPart

		if strings.ContainsAny(encodedValue, " $'") {
			node := new(syntax.SglQuoted)
			node.Left = syntax.Pos{}
			node.Right = syntax.Pos{}
			node.Value = encodedValue

			wordPart = syntax.WordPart(node)
		} else {
			node := new(syntax.Lit)
			node.ValuePos = syntax.Pos{}
			node.ValueEnd = syntax.Pos{}
			node.Value = encodedValue

			wordPart = syntax.WordPart(node)
		}

		cmd.Args[a] = new(syntax.Word)
		cmd.Args[a].Parts = []syntax.WordPart{wordPart}
	}

	return cmd, nil
}

func info(thread *starlark.Thread, msg string, args ...interface{}) {
	ctx := getCtx(thread)
	pos := thread.CallFrame(1).Pos

	filepath := simplifyPath(ctx, ctx.filepath)

	log(ctx.ctx).Info().
		Msgf("%s:%d:%d: %s", filepath, pos.Line, pos.Col, fmt.Sprintf(msg, args...))
}

func warn(thread *starlark.Thread, msg string, args ...interface{}) {
	ctx := getCtx(thread)
	pos := thread.CallFrame(1).Pos

	filepath := simplifyPath(ctx, ctx.filepath)

	log(ctx.ctx).Warn().
		Msgf("%s:%d:%d: %s", filepath, pos.Line, pos.Col, fmt.Sprintf(msg, args...))
}

// * Builtin functions

func option(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var name string
	var defaultValue starlark.String
	var help string

	err := starlark.UnpackArgs(fn.Name(), args, kwargs, "name", &name, "default?", &defaultValue, "help?", &help)
	if err != nil {
		return nil, err
	}

	ctx := getCtx(thread)
	if !ctx.initPhase {
		return nil, eris.New("can only be called during the init phase (in the global scope)")
	}

	ctx.options[name] = ScriptOption{
		DefaultValue: defaultValue,
		Help:         help,
	}

	value, ok := ctx.optionValues[name]
	if ok {
		return starlark.String(value), nil
	}

	return defaultValue, nil
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

	if task.Short == "configure" {
		return nil, eris.New(`the task name "configure" is reserved, please use a different name`)
	}

	task.Env = map[string]string{}

	if task.Base == "" {
		task.Base = "."
	}
	task.Base = normalizePath(getCtx(thread), task.Base)

	task.Deps, err = starlarkIterable2stringSlice(deps, "deps")
	if err != nil {
		return nil, err
	}

	task.SkipIfExists, err = starlarkIterable2stringSlice(skipIfExists, "skip_if_exists")
	if err != nil {
		return nil, err
	}

	task.Inputs, err = starlarkIterable2stringSlice(inputs, "inputs")
	if err != nil {
		return nil, err
	}

	task.Outputs, err = starlarkIterable2stringSlice(outputs, "outputs")
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

	strBuffer := strings.Builder{}
	printer := syntax.NewPrinter(syntax.Minify(true))
	parser := syntax.NewParser()
	task.Cmds = make([]TaskCmd, 0)
	iter := cmds.Iterate()
	defer iter.Done()

	var item starlark.Value
	idx := 0
	for iter.Next(&item) {
		switch value := item.(type) {
		case starlark.String:
			task.Cmds = append(task.Cmds, TaskCmdScript{Content: value.GoString()})
		case starlark.Tuple:
			cmd, err := processCmdParts(value, parser, task.Base)
			if err != nil {
				return nil, eris.Wrapf(err, "failed to process command #%d", idx)
			}

			strBuffer.Reset()
			err = printer.Print(&strBuffer, cmd)
			if err != nil {
				return nil, eris.Wrapf(err, "failed to process command #%d", idx)
			}

			task.Cmds = append(task.Cmds, TaskCmdScript{Content: strBuffer.String()})
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
				return nil, eris.Wrapf(err, "failed to process command #%d", idx)
			}

			strBuffer.Reset()
			err = printer.Print(&strBuffer, cmd)
			if err != nil {
				return nil, eris.Wrapf(err, "failed to process command #%d", idx)
			}

			task.Cmds = append(task.Cmds, TaskCmdScript{Content: strBuffer.String()})
		case *Task:
			task.Cmds = append(task.Cmds, TaskCmdTaskRef{Task: value})
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
		ctx := getCtx(thread)
		ctx.tasks = append(ctx.tasks, task)
	}
	return task, nil
}

// RunScript executes a starlake scripts and returns the declared options. If doConfigure is true, the script's
// configure function is called and the declared tasks are collected and returned.
func RunScript(ctx context.Context, filename, projectRoot string, options map[string]string, doConfigure bool) (TaskList, map[string]ScriptOption, error) {
	projectRoot, err := filepath.Abs(projectRoot)
	if err != nil {
		return nil, nil, err
	}

	filename, err = filepath.Abs(filename)
	if err != nil {
		return nil, nil, err
	}

	builtins := starlark.StringDict{
		"OS":           starlark.String(runtime.GOOS),
		"ARCH":         starlark.String(runtime.GOARCH),
		"info":         starlark.NewBuiltin("info", starInfo),
		"warn":         starlark.NewBuiltin("warn", starWarn),
		"error":        starlark.NewBuiltin("error", starError),
		"resolve_path": starlark.NewBuiltin("resolve_path", resolvePath),
		"option":       starlark.NewBuiltin("option", option),
		"getenv":       starlark.NewBuiltin("getenv", getenv),
		"setenv":       starlark.NewBuiltin("setenv", setenv),
		"prepend_path": starlark.NewBuiltin("prepend_path", prependPathDir),
		"read_yaml":    starlark.NewBuiltin("read_yaml", readYaml),
		"isdir":        starlark.NewBuiltin("isdir", starIsdir),
		"isfile":       starlark.NewBuiltin("isfile", starIsfile),
		"execute":      starlark.NewBuiltin("execute", starExec),
		"task":         starlark.NewBuiltin("task", task),
		"load_vcvars":  starlark.NewBuiltin("load_vcvars", starLoadVcvars),
	}

	thread := &starlark.Thread{
		Name: "main",
		Print: func(thread *starlark.Thread, msg string) {
			log(ctx).Info().Str("thread", thread.Name).Msg(msg)
		},
	}
	threadCtx := parserCtx{
		ctx:          ctx,
		filepath:     filename,
		projectRoot:  projectRoot,
		options:      make(map[string]ScriptOption),
		optionValues: options,
		envOverrides: make(map[string]string, 0),
		tasks:        make([]*Task, 0),
		yamlCache:    make(map[string]interface{}),
		initPhase:    true,
	}
	thread.SetLocal("parserCtx", &threadCtx)

	script, err := ioutil.ReadFile(filename)
	if err != nil {
		return nil, nil, eris.Wrapf(err, "failed to read file")
	}

	// wrap the entire script in a function to work around the limitation that ifs are only allowed inside functions
	globals, err := starlark.ExecFile(thread, simplifyPath(&threadCtx, filename), script, builtins)
	if err != nil {
		if evalError, ok := err.(*starlark.EvalError); ok {
			return nil, nil, eris.Errorf("failed to execute %s:\n%s", simplifyPath(&threadCtx, filename), evalError.Backtrace())
		}
		return nil, nil, eris.Wrap(err, "failed to execute")
	}

	tasks := TaskList{}
	if doConfigure {
		configure, ok := globals["configure"]
		if !ok {
			return nil, nil, eris.Errorf("%s did not declare a configure function", simplifyPath(&threadCtx, filename))
		}

		configureFunc, ok := configure.(starlark.Callable)
		if !ok {
			return nil, nil, eris.Errorf("%s did declare a configure value but it's not a function", simplifyPath(&threadCtx, filename))
		}

		threadCtx.initPhase = false
		_, err = starlark.Call(thread, configureFunc, make(starlark.Tuple, 0), make([]starlark.Tuple, 0))
		if err != nil {
			if evalError, ok := err.(*starlark.EvalError); ok {
				return nil, nil, eris.New(evalError.Backtrace())
			}
			return nil, nil, eris.Wrapf(err, "failed configure call in %s", simplifyPath(&threadCtx, filename))
		}

		for _, task := range threadCtx.tasks {
			tasks[task.Short] = task

			for name, value := range threadCtx.envOverrides {
				_, present := task.Env[name]
				if !present {
					task.Env[name] = value
				}
			}
		}
	}

	return tasks, threadCtx.options, nil
}
