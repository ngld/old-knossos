// +build tools

package main

import (
	_ "github.com/cortesi/modd/cmd/modd"
	_ "github.com/go-task/task/v3/cmd/task"
	_ "github.com/golang/protobuf/protoc-gen-go"
	_ "github.com/jschaf/pggen/cmd/pggen"
	_ "github.com/twitchtv/twirp/protoc-gen-twirp"
)
