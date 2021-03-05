package buildsys

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strconv"
	"strings"

	"github.com/rotisserie/eris"
	"go.starlark.net/starlark"
	"gopkg.in/yaml.v3"
	"mvdan.cc/sh/v3/expand"
	"mvdan.cc/sh/v3/interp"
	"mvdan.cc/sh/v3/syntax"
)

func resolvePath(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	base := ""
	ctx := getCtx(thread)

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

				base = normalizePath(ctx, base)
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

	normPath := normalizePath(ctx, parts...)
	if base != "" {
		var err error
		normPath, err = filepath.Rel(base, normPath)
		if err != nil {
			return nil, err
		}
	}

	return StarlarkPath(normPath), nil
}

func starInfo(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var message string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &message)
	if err != nil {
		return nil, err
	}

	info(thread, message)
	return starlark.None, nil
}

func starWarn(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var message string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &message)
	if err != nil {
		return nil, err
	}

	warn(thread, message)
	return starlark.None, nil
}

func starError(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var message string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &message)
	if err != nil {
		return nil, err
	}

	return nil, eris.New(message)
}

func getenv(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var key string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &key)
	if err != nil {
		return nil, err
	}

	envOverrides := getCtx(thread).envOverrides
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

	envOverrides := getCtx(thread).envOverrides
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

	envOverrides := getCtx(thread).envOverrides
	path, ok := envOverrides["PATH"]
	if !ok {
		path = os.Getenv("PATH")
	}

	envOverrides["PATH"] = normalizePath(getCtx(thread), pathDir) + string(os.PathListSeparator) + path

	return starlark.String(envOverrides["PATH"]), nil
}

func readYaml(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var yamlFile string
	var yamlKey string
	var defaultValue starlark.Value

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 2, &yamlFile, &yamlKey, &defaultValue)
	if err != nil {
		return nil, err
	}

	yamlFile = normalizePath(getCtx(thread), yamlFile)

	cache := getCtx(thread).yamlCache
	doc, loaded := cache[yamlFile]
	if !loaded {
		content, err := ioutil.ReadFile(yamlFile)
		if err != nil {
			return nil, eris.Wrapf(err, "failed to open file %s", yamlFile)
		}

		err = yaml.Unmarshal(content, &doc)
		if err != nil {
			return nil, eris.Wrapf(err, "failed to parse file %s", yamlFile)
		}
	}

	// parse the key
	value := reflect.ValueOf(doc)
	for _, key := range strings.Split(yamlKey, ".") {
		switch value.Kind() {
		case reflect.Map:
			value = value.MapIndex(reflect.ValueOf(key))
		case reflect.Slice:
			idx, err := strconv.Atoi(key)
			if err != nil {
				value = reflect.ValueOf(nil)
				goto endLoop
			} else {
				if idx >= value.Len() {
					value = reflect.ValueOf(nil)
					goto endLoop
				}
				value = value.Index(idx)
			}
		case reflect.Invalid:
			goto endLoop
		default:
			return nil, eris.Errorf("encountered unexpected value of kind %v in YAML document", value.Kind())
		}
	}

endLoop:
	if value.Kind() == reflect.Invalid || value.IsNil() {
		return defaultValue, nil
	} else {
		switch value := value.Interface().(type) {
		case string:
			return starlark.String(value), nil
		case int:
			return starlark.MakeInt(value), nil
		case bool:
			return starlark.Bool(value), nil
		default:
			return nil, eris.Errorf("can't return value %v", value)
		}
	}
}

func starIsdir(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var dirPath string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &dirPath)
	if err != nil {
		return nil, err
	}

	dirPath = normalizePath(getCtx(thread), dirPath)
	info, err := os.Stat(dirPath)
	if err == nil && info.IsDir() {
		return starlark.True, nil
	} else {
		return starlark.False, nil
	}
}

func starIsfile(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var filePath string

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 1, &filePath)
	if err != nil {
		return nil, err
	}

	filePath = normalizePath(getCtx(thread), filePath)
	info, err := os.Stat(filePath)
	if err == nil && info.Mode().IsRegular() {
		return starlark.True, nil
	} else {
		return starlark.False, nil
	}
}

func starExec(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	var command starlark.Value
	var outputFormat string
	var showError bool

	err := starlark.UnpackArgs(fn.Name(), args, kwargs, "command", &command, "format?", &outputFormat, "show_error?", &showError)
	if err != nil {
		return nil, err
	}

	if outputFormat == "" {
		outputFormat = "text"
	}

	if outputFormat != "text" && outputFormat != "json" {
		return nil, eris.Errorf("unsupported format %s", outputFormat)
	}

	var shellCmd []syntax.Node
	parser := syntax.NewParser()
	ctx := getCtx(thread)
	base := filepath.Dir(ctx.filepath)

	switch command := command.(type) {
	case starlark.String:
		part := TaskCmdScript{
			TaskName: fn.Name(),
			Index:    0,
			Content:  command.GoString(),
		}

		stmts, err := part.ToShellStmts(parser)
		if err != nil {
			return nil, err
		}

		shellCmd = make([]syntax.Node, len(stmts))
		for idx, stmt := range stmts {
			shellCmd[idx] = stmt
		}
	case starlark.Tuple:
		expr, err := processCmdParts(command, parser, base)
		if err != nil {
			return nil, err
		}

		shellCmd = []syntax.Node{expr}
	default:
		return nil, eris.Errorf("unexpected type %s for command parameter, only strings and tuples are valid", command.Type())
	}

	outputBuffer := strings.Builder{}
	errOut := os.Stderr

	if !showError {
		errOut = nil
	}

	runner, err := interp.New(
		interp.Dir(base),
		interp.Env(expand.ListEnviron(getEnvVars(ctx)...)),
		interp.ExecHandler(execHandler),
		interp.OpenHandler(openHandler),
		interp.StdIO(nil, &outputBuffer, errOut),
		interp.Params("-e"),
	)
	if err != nil {
		return nil, eris.Wrap(err, "failed to initialize runner")
	}

	success := true
	for _, cmd := range shellCmd {
		err := runner.Run(ctx.ctx, cmd)
		if err != nil {
			if showError {
				log(ctx.ctx).Error().Err(err).Msg("shell error")
			}
			success = false
			break
		}
	}

	if !success {
		return starlark.False, nil
	}

	if outputFormat == "json" {
		var decoded interface{}
		err = json.Unmarshal([]byte(outputBuffer.String()), &decoded)
		if err != nil {
			return nil, eris.Wrap(err, "failed to parse command output")
		}

		return interfaceToStarlark(thread, decoded)
	}

	return starlark.String(outputBuffer.String()), nil
}

func starLoadVcvars(thread *starlark.Thread, fn *starlark.Builtin, args starlark.Tuple, kwargs []starlark.Tuple) (starlark.Value, error) {
	arch := "amd64"

	err := starlark.UnpackPositionalArgs(fn.Name(), args, kwargs, 0, &arch)
	if err != nil {
		return nil, err
	}

	if runtime.GOOS != "windows" {
		return starlark.True, nil
	}

	ctx := getCtx(thread)

	vsWherePath := "C:\\Program Files (x86)\\Microsoft Visual Studio\\Installer\\vswhere.exe"
	cmd := exec.Command(vsWherePath, "-property", "installationPath", "-latest")
	output, err := cmd.Output()
	if err != nil {
		return nil, eris.Wrapf(err, "failed to run %s", vsWherePath)
	}

	vsPath := strings.Trim(string(output), " \r\n")
	if vsPath == "" {
		return nil, eris.New("No Visual Studio installation found. If you recently updated VS, you might have to restart your PC.")
	}

	info, err := os.Stat(vsPath)
	if err != nil {
		return nil, eris.Wrap(err, "failed to check VS installation directory")
	}

	if !info.IsDir() {
		return nil, eris.Errorf("the detected VS installation path %s does not exist", vsPath)
	}

	vcvarsall := filepath.Join(vsPath, "VC", "Auxiliary", "Build", "vcvarsall.bat")
	_, err = os.Stat(vcvarsall)
	if err != nil {
		return nil, eris.Wrap(err, "could not find vcvarsall.bat")
	}

	tmpDir := filepath.Join(os.TempDir(), fmt.Sprintf("knbuildsys-%d", rand.Int()))
	err = os.Mkdir(tmpDir, 0700)
	if err != nil {
		return nil, eris.Wrap(err, "could not create temporary directory")
	}
	defer os.RemoveAll(tmpDir)

	script := filepath.Join(tmpDir, "vchelper.bat")
	err = ioutil.WriteFile(script, []byte(`@echo off
call "`+vcvarsall+`" %*
echo KN_PATH=%PATH%
echo KN_INCLUDE=%INCLUDE%
echo KN_LIBPATH=%LIBPATH%
echo KN_LIB=%LIB%
`), 0700)
	if err != nil {
		return nil, eris.Wrap(err, "failed to write helper script")
	}

	cmd = exec.Command("cmd", "/C", script, arch)
	cmd.Env = getEnvVars(ctx)
	output, err = cmd.Output()
	if err != nil {
		return nil, eris.Wrap(err, "failed to run helper script")
	}

	for _, line := range strings.Split(string(output), "\r\n") {
		if strings.HasPrefix(line, "KN_") {
			parts := strings.SplitN(line, "=", 2)
			if len(parts) < 2 {
				log(ctx.ctx).Error().Msgf("vchelper produced malformed line %s", line)
			} else {
				ctx.envOverrides[parts[0][3:]] = parts[1]
			}
		}
	}

	return starlark.True, nil
}
