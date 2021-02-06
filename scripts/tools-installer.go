package main

import (
	"fmt"
	"go/parser"
	"go/token"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

func main() {
	_, mypath, _, ok := runtime.Caller(0)
	if !ok {
		fmt.Println("Failed: Could not determine location of tools-installer.go")
		os.Exit(1)
	}

	pkgPath := filepath.Join(filepath.Dir(mypath), "../packages")
	binPath := filepath.Join(filepath.Dir(mypath), "../.tools")

	pkgDir, err := os.Open(pkgPath)
	if err != nil {
		panic(err)
	}
	defer pkgDir.Close()
	subdirs, err := pkgDir.Readdir(0)
	if err != nil {
		panic(err)
	}

	for _, pkg := range subdirs {
		if pkg.IsDir() {
			toolsFile := filepath.Join(pkgPath, pkg.Name(), "tools.go")
			if _, err := os.Stat(toolsFile); !os.IsNotExist(err) {
				fmt.Println(">", pkg.Name())

				fset := token.NewFileSet()
				f, err := parser.ParseFile(fset, toolsFile, nil, parser.ImportsOnly)
				if err != nil {
					panic(err)
				}

				for _, path := range f.Imports {
					dep := strings.Trim(path.Path.Value, `"`)
					// fmt.Println("# go install", dep)

					cmd := exec.Command("go", "install", "-v", dep)
					cmd.Dir = filepath.Dir(toolsFile)
					cmd.Env = append(os.Environ(), fmt.Sprintf("GOBIN=%s", binPath))
					cmd.Stderr = os.Stderr
					cmd.Stdout = os.Stdout
					err := cmd.Run()
					if err != nil {
						panic(err)
					}
				}
			}
		}
	}
}
