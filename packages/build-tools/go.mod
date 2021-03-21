module github.com/ngld/knossos/packages/build-tools

go 1.15

require (
	github.com/aidarkhanov/nanoid v1.0.8
	github.com/andybalholm/brotli v1.0.1
	github.com/containerd/containerd v1.4.4 // indirect
	github.com/cortesi/modd v0.0.0-20210222043654-cbdcc23af7d5
	github.com/docker/docker v20.10.5+incompatible // indirect
	github.com/golang/protobuf v1.5.1
	github.com/jackc/pgproto3/v2 v2.0.7 // indirect
	github.com/jschaf/pggen v0.0.0-20210320184937-c16cfaa8a7dd
	github.com/mitchellh/colorstring v0.0.0-20190213212951-d06e56a500db
	github.com/rotisserie/eris v0.5.0
	github.com/rs/zerolog v1.20.0
	github.com/schollz/progressbar/v3 v3.7.6
	github.com/sirupsen/logrus v1.8.1 // indirect
	github.com/spf13/cobra v1.1.3
	github.com/twitchtv/twirp v7.1.1+incompatible
	github.com/ulikunitz/xz v0.5.10
	go.starlark.net v0.0.0-20210312235212-74c10e2c17dc
	go.uber.org/multierr v1.6.0 // indirect
	go.uber.org/zap v1.16.0 // indirect
	golang.org/x/crypto v0.0.0-20210317152858-513c2a44f670 // indirect
	golang.org/x/mod v0.4.2 // indirect
	golang.org/x/net v0.0.0-20210316092652-d523dce5a7f4 // indirect
	golang.org/x/sys v0.0.0-20210320140829-1e4c9ba3b0c4 // indirect
	golang.org/x/term v0.0.0-20210317153231-de623e64d2a6 // indirect
	golang.org/x/text v0.3.5 // indirect
	google.golang.org/genproto v0.0.0-20210319143718-93e7006c17a6 // indirect
	google.golang.org/grpc v1.36.0 // indirect
	gopkg.in/yaml.v3 v3.0.0-20210107192922-496545a6307b
	mvdan.cc/sh/v3 v3.3.0-0.dev.0.20210226093739-3d8d47845eeb
)

replace github.com/ngld/knossos/packages/libknossos => ../libknossos

replace github.com/ngld/knossos/packages/libarchive => ../libarchive

replace github.com/ngld/knossos/packages/api => ../api
