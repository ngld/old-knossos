package pkg

import (
	"fmt"
	"go/parser"
	"go/token"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

func InstallTools() error {
	projectRoot, err := GetProjectRoot()
	if err != nil {
		return err
	}

	binPath := filepath.Join(projectRoot, ".tools")
	toolsFile := filepath.Join(projectRoot, "packages", "build-tools", "tools.go")

	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, toolsFile, nil, parser.ImportsOnly)
	if err != nil {
		return err
	}

	for _, path := range f.Imports {
		dep := strings.Trim(path.Path.Value, `"`)
		// fmt.Println("# go install", dep)

		cmd := exec.Command("go", "install", dep)
		cmd.Dir = filepath.Dir(toolsFile)
		cmd.Env = append(os.Environ(), fmt.Sprintf("GOBIN=%s", binPath))
		cmd.Stderr = os.Stderr
		cmd.Stdout = os.Stdout
		err := cmd.Run()
		if err != nil {
			return err
		}
	}

	return nil
}
