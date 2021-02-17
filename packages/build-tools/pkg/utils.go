package pkg

import (
	"os"
	"path/filepath"
	"runtime"

	"github.com/mitchellh/colorstring"
	"github.com/rotisserie/eris"
)

func GetProjectRoot() (string, error) {
	_, mypath, _, ok := runtime.Caller(0)
	if !ok {
		return "", eris.New("Failed to determine script path!")
	}

	mypath = filepath.Dir(mypath)
	for {
		gitPath := filepath.Join(mypath, ".git")
		_, err := os.Stat(gitPath)
		if err == nil {
			return mypath, nil
		}

		if !eris.Is(err, os.ErrNotExist) {
			return "", eris.Wrap(err, "Error ocurred while searching for project root")
		}

		nextPath := filepath.Dir(mypath)
		if mypath == nextPath {
			break
		}
		mypath = nextPath
	}

	return "", eris.New("Project root not found")
}

func PrintTask(msg string) {
	colorstring.Printf("[blue][bold]==>[default] %s\n", msg)
}

func PrintSubtask(msg string) {
	colorstring.Printf("[green][bold]  ->[reset] %s\n", msg)
}

func PrintError(msg string) {
	colorstring.Printf("[red][bold]  ->[reset] %s\n", msg)
}
