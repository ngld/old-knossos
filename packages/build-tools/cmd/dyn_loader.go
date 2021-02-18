package cmd

import (
	"io/ioutil"
	"os"
	"strings"

	"github.com/rotisserie/eris"
	"github.com/spf13/cobra"
)

var genDynLoaderCmd = &cobra.Command{
	Use:   "gen-dyn-loader <path to cgo header> <output header>",
	Short: "Generates a runtime library loader (dlopen/LoadLibrary)",
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) != 2 {
			return eris.Errorf("Expected 2 arguments but got %d!", len(args))
		}
		return genLoader(args[0], args[1])
	},
}

func init() {
	rootCmd.AddCommand(genDynLoaderCmd)
}

func fixTypes(input string) string {
	winFix := strings.ReplaceAll(input, "__SIZE_TYPE__", "size_t")

	if strings.Contains(input, "Complex") {
		// We don't need complex types so don't bother
		winFix = ""
	}

	if winFix != input {
		return "#ifdef WIN32\n" + winFix + "\n#else\n" + input + "\n#endif\n"
	}
	return input
}

func genLoader(headerFile, dynHeader string) error {
	dynLoader := strings.ReplaceAll(dynHeader, ".h", ".cc")
	if dynLoader == dynHeader {
		return eris.Errorf("Generated loader file name is the same as the header file?! (%s) Does the header end with .h?", dynLoader)
	}

	headerContent, err := ioutil.ReadFile(headerFile)
	if err != nil {
		return err
	}

	header := strings.Builder{}
	loaderDecl := strings.Builder{}
	loaderFunc := strings.Builder{}

	header.WriteString("#ifndef KNOSSOS_BRAIN_LOADER\n")
	header.WriteString("#define KNOSSOS_BRAIN_LOADER\n\n")

	headerLines := strings.Split(string(headerContent), "\n")
	inPreamble := false
	for _, line := range headerLines {
		if inPreamble && !strings.HasPrefix(line, "extern ") {
			if line == "/* End of preamble from import \"C\" comments.  */" {
				inPreamble = false
			} else {
				header.WriteString(line + "\n")
			}
		} else if strings.HasPrefix(line, "#define ") ||
			strings.HasPrefix(line, "typedef ") ||
			strings.HasPrefix(line, "#include ") ||
			strings.HasPrefix(line, "//") {
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
			loaderFunc.WriteString(") LOAD_SYM(lib, \"")
			loaderFunc.WriteString(funcName)
			loaderFunc.WriteString("\");\n")
		} else if line == "/* Start of preamble from import \"C\" comments.  */" {
			inPreamble = true
		}
	}

	header.WriteString("\nbool LoadKnossos(const char* knossos_path, char** error);\n\n")
	header.WriteString("#endif\n")

	loader := strings.Builder{}
	loader.WriteString("#ifdef WIN32\n")
	loader.WriteString("#include <windows.h>\n")
	loader.WriteString("\n")
	loader.WriteString("#define LOAD_SYM GetProcAddress\n")
	loader.WriteString("#else\n")
	loader.WriteString("#include <dlfcn.h>\n")
	loader.WriteString("\n")
	loader.WriteString("#define LOAD_SYM dlsym\n")
	loader.WriteString("#endif\n")

	loader.WriteString("#include \"dynknossos.h\"\n\n")
	loader.WriteString(loaderDecl.String())

	loader.WriteString("\n\nbool LoadKnossos(const char* knossos_path, char** error) {\n")
	loader.WriteString("#ifdef WIN32\n")
	loader.WriteString("  HMODULE lib = LoadLibraryA(knossos_path);\n")
	loader.WriteString("  if (!lib) {\n")
	loader.WriteString("    auto code = GetLastError();\n")
	loader.WriteString("    LPSTR message;\n")
	loader.WriteString("    FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,\n")
	loader.WriteString("       nullptr, code, 0, (LPSTR)&message, 0, nullptr);\n")
	loader.WriteString("    *error = (char*) message;\n")
	loader.WriteString("    return false;\n")
	loader.WriteString("  }\n\n")
	loader.WriteString("#else\n")
	loader.WriteString("  void* lib = dlopen(knossos_path, RTLD_NOW | RTLD_NODELETE);\n")
	loader.WriteString("  if (!lib) {\n")
	loader.WriteString("    *error = dlerror();\n")
	loader.WriteString("    return false;\n")
	loader.WriteString("  }\n\n")
	loader.WriteString("#endif\n")

	loader.WriteString(loaderFunc.String())

	loader.WriteString("#ifndef WIN32\n")
	loader.WriteString("\n  dlclose(lib);\n")
	loader.WriteString("#endif\n")

	loader.WriteString("  return true;\n")
	loader.WriteString("}\n\n")

	writer, err := os.Create(dynHeader)
	if err != nil {
		return err
	}

	_, err = writer.WriteString(header.String())
	if err != nil {
		return err
	}
	err = writer.Close()
	if err != nil {
		return err
	}

	writer, err = os.Create(dynLoader)
	if err != nil {
		return err
	}

	_, err = writer.WriteString(loader.String())
	if err != nil {
		return err
	}

	err = writer.Close()
	if err != nil {
		return err
	}

	return nil
}
