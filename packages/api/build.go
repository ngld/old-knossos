package main

//go:generate protoc -I./definitions ./definitions/mod.proto --plugin=../../.tools/protoc-gen-go --go_out=api --go_opt=paths=source_relative
//go:generate protoc -I./definitions ./definitions/service.proto --plugin=../../.tools/protoc-gen-go --plugin=../../.tools/protoc-gen-twirp --go_out=api --twirp_out=api --go_opt=paths=source_relative
//go:generate mv api/github.com/ngld/knossos/packages/api/api/service.twirp.go api
//go:generate rm -r api/github.com
