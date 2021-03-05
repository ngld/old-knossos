package buildsys

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"

	"github.com/rotisserie/eris"
	"go.starlark.net/starlark"
)

func normalizePath(ctx *parserCtx, pathList ...string) string {
	result := filepath.Dir(ctx.filepath)

	for _, path := range pathList {
		if strings.HasPrefix(path, "//") {
			result = filepath.Join(ctx.projectRoot, path[2:])
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

func simplifyPath(ctx *parserCtx, path string) string {
	projectRoot := ctx.projectRoot
	absPath, err := filepath.Abs(path)
	if err != nil {
		return path
	}

	if strings.HasPrefix(absPath, projectRoot) {
		return "//" + absPath[len(projectRoot)+1:]
	}
	return path
}

func getEnvVars(ctx *parserCtx) []string {
	osEnv := os.Environ()
	shellEnv := make([]string, 0, len(osEnv)+len(ctx.envOverrides))
	for _, item := range osEnv {
		parts := strings.SplitN(item, "=", 2)
		if runtime.GOOS == "windows" {
			parts[0] = strings.ToUpper(parts[0])
		}

		// skip overriden entries to avoid conflicts
		if _, present := ctx.envOverrides[parts[0]]; !present {
			shellEnv = append(shellEnv, item)
		}
	}

	for k, v := range ctx.envOverrides {
		shellEnv = append(shellEnv, fmt.Sprintf("%s=%s", k, v))
	}

	return shellEnv
}

func interfaceToStarlark(thread *starlark.Thread, value interface{}) (starlark.Value, error) {
	// handle a few simple and common cases first
	switch value := value.(type) {
	case string:
		return starlark.String(value), nil
	case int:
		return starlark.MakeInt(value), nil
	case bool:
		if value {
			return starlark.True, nil
		} else {
			return starlark.False, nil
		}
	case float32:
		return starlark.Float(value), nil
	case float64:
		return starlark.Float(value), nil
	case []string:
		items := make(starlark.Tuple, len(value))
		for idx, raw := range value {
			items[idx] = starlark.String(raw)
		}

		return items, nil
	case map[string]string:
		dict := starlark.NewDict(len(value))
		for k, v := range value {
			err := dict.SetKey(starlark.String(k), starlark.String(v))
			if err != nil {
				return nil, err
			}
		}

		return dict, nil
	}

	refValue := reflect.ValueOf(value)
	if refValue.IsNil() {
		return starlark.None, nil
	}

	var err error
	switch refValue.Kind() {
	case reflect.Slice:
		fallthrough
	case reflect.Array:
		tuple := make(starlark.Tuple, refValue.Len())
		for idx := 0; idx < refValue.Len(); idx++ {
			tuple[idx], err = interfaceToStarlark(thread, refValue.Index(idx).Interface())
			if err != nil {
				return nil, err
			}
		}

		return tuple, nil
	case reflect.Map:
		dict := starlark.NewDict(refValue.Len())
		iter := refValue.MapRange()
		for iter.Next() {
			key, err := interfaceToStarlark(thread, iter.Key().Interface())
			if err != nil {
				return nil, err
			}

			value, err := interfaceToStarlark(thread, iter.Value().Interface())
			if err != nil {
				return nil, err
			}

			err = dict.SetKey(key, value)
			if err != nil {
				return nil, err
			}
		}

		return dict, nil
	}

	return nil, eris.Errorf("encountered unsupported type %v", refValue.Kind())
}
