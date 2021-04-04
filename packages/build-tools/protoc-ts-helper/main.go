package main

import (
	"os"
	"os/exec"
)

func main() {
	cmd := exec.Command("node")
	cmd.Args = append([]string{"node", "-e", "require('@protobuf-ts/plugin/bin/protoc-gen-ts')"}, os.Args[:1]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()
	if err != nil {
		panic(err)
	}
}
