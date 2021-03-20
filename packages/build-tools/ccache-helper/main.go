package main

import (
	"os"
	"os/exec"
)

func main() {
	cmd := exec.Command("ccache")
	cmd.Args = append([]string{"ccache", os.Getenv("GCCPATH")}, os.Args[1:]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()
	if err != nil {
		panic(err)
	}
}
