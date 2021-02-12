package main

import (
	"io/ioutil"
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

func fixTypes(input string) string {
	if runtime.GOOS == "windows" {
		input = strings.ReplaceAll(input, "__SIZE_TYPE__", "size_t")

		if strings.Contains(input, "Complex") {
			// We don't need complex types so don't bother
			input = ""
		}
	}

	return input
}

func main() {
	_, myFile, _, _ := runtime.Caller(0)
	buildPath := filepath.Join(filepath.Dir(myFile), "../build")
	headerFile := filepath.Join(buildPath, "libbrain.h")
	dynHeader := filepath.Join(buildPath, "dynbrain.h")
	dynLoader := filepath.Join(buildPath, "dynbrain.cc")
	headerContent, err := ioutil.ReadFile(headerFile)
	if err != nil {
		panic(err)
	}

	header := strings.Builder{}
	loaderDecl := strings.Builder{}
	loaderFunc := strings.Builder{}

	header.WriteString("#ifndef KNOSSOS_BRAIN_LOADER\n")
	header.WriteString("#define KNOSSOS_BRAIN_LOADER\n\n")

	headerLines := strings.Split(string(headerContent), "\n")
	for _, line := range headerLines {
		if strings.HasPrefix(line, "#define ") ||
			strings.HasPrefix(line, "typedef ") ||
			strings.HasPrefix(line, "#include ") {
			header.WriteString(fixTypes(line) + "\n")
		} else if strings.HasPrefix(line, "extern ") && !strings.HasPrefix(line, "extern \"C\"") {
			parts := strings.SplitN(line, " ", 3)
			returnType := parts[1]
			parts = strings.SplitN(parts[2], "(", 2)
			funcName := parts[0]
			rest := parts[1]

			header.WriteString("typedef ")
			header.WriteString(returnType)
			header.WriteString(" (*GODYN_")
			header.WriteString(funcName)
			header.WriteString(")(")
			header.WriteString(rest)
			header.WriteString("\n")

			header.WriteString("extern GODYN_")
			header.WriteString(funcName)
			header.WriteString(" ")
			header.WriteString(funcName)
			header.WriteString(";\n")

			loaderDecl.WriteString("GODYN_")
			loaderDecl.WriteString(funcName)
			loaderDecl.WriteString(" ")
			loaderDecl.WriteString(funcName)
			loaderDecl.WriteString(" = 0;\n")

			loaderFunc.WriteString(funcName)
			loaderFunc.WriteString(" = (GODYN_")
			loaderFunc.WriteString(funcName)
			if runtime.GOOS == "windows" {
				loaderFunc.WriteString(") GetProcAddress(lib, \"")
			} else {
				loaderFunc.WriteString(") dlsym(lib, \"")
			}
			loaderFunc.WriteString(funcName)
			loaderFunc.WriteString("\");\n")
		}
	}

	header.WriteString("\nbool LoadBrain(const char* brain_path, char** error);\n\n")
	header.WriteString("#endif\n")

	loader := strings.Builder{}
	if runtime.GOOS == "windows" {
		loader.WriteString("#include <windows.h>\n")
	} else {
		loader.WriteString("#include <dlfcn.h>\n")
	}
	loader.WriteString("#include \"dynbrain.h\"\n\n")
	loader.WriteString(loaderDecl.String())
	loader.WriteString("\n\nbool LoadBrain(const char* brain_path, char** error) {\n")
	if runtime.GOOS == "windows" {
		loader.WriteString("  HMODULE lib = LoadLibraryA(brain_path);\n")
		loader.WriteString("  if (!lib) {\n")
		loader.WriteString("    auto code = GetLastError();\n")
		loader.WriteString("    LPSTR message;\n")
		loader.WriteString("    FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,\n")
		loader.WriteString("       nullptr, code, 0, (LPSTR)&message, 0, nullptr);\n")
		loader.WriteString("    *error = (char*) message;\n")
		loader.WriteString("    return false;\n")
		loader.WriteString("  }\n\n")
	} else {
		loader.WriteString("  void* lib = dlopen(brain_path, RTLD_NOW | RTLD_NODELETE);\n")
		loader.WriteString("  if (!lib) {\n")
		loader.WriteString("    *error = dlerror();\n")
		loader.WriteString("    return false;\n")
		loader.WriteString("  }\n\n")
	}
	loader.WriteString(loaderFunc.String())
	if runtime.GOOS != "windows" {
		loader.WriteString("\n  dlclose(lib);\n")
	}
	loader.WriteString("  return true;\n")
	loader.WriteString("}\n\n")

	writer, err := os.Create(dynHeader)
	if err != nil {
		panic(err)
	}

	_, err = writer.WriteString(header.String())
	if err != nil {
		panic(err)
	}
	err = writer.Close()
	if err != nil {
		panic(err)
	}

	writer, err = os.Create(dynLoader)
	if err != nil {
		panic(err)
	}

	_, err = writer.WriteString(loader.String())
	if err != nil {
		panic(err)
	}

	err = writer.Close()
	if err != nil {
		panic(err)
	}
}
