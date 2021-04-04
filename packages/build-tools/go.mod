module github.com/ngld/knossos/packages/build-tools

go 1.15

require (
	github.com/aidarkhanov/nanoid v1.0.8
	github.com/andybalholm/brotli v1.0.1
	github.com/containerd/containerd v1.4.4 // indirect
	github.com/cortesi/modd v0.0.0-20210323234521-b35eddab86cc
	github.com/cortesi/moddwatch v0.0.0-20210323234936-df014e95c743 // indirect
	github.com/docker/docker v20.10.5+incompatible // indirect
	github.com/golang/protobuf v1.5.2
	github.com/jackc/pgproto3/v2 v2.0.7 // indirect
	github.com/jackc/pgx/v4 v4.11.0 // indirect
	github.com/jschaf/pggen v0.0.0-20210331000841-06eb603fa525
	github.com/mattn/go-runewidth v0.0.12 // indirect
	github.com/mitchellh/colorstring v0.0.0-20190213212951-d06e56a500db
	github.com/rakyll/statik v0.1.7 // indirect
	github.com/rotisserie/eris v0.5.0
	github.com/rs/zerolog v1.21.0
	github.com/schollz/progressbar/v3 v3.7.6
	github.com/sirupsen/logrus v1.8.1 // indirect
	github.com/spf13/cobra v1.1.3
	github.com/twitchtv/twirp v7.1.1+incompatible
	github.com/ulikunitz/xz v0.5.10
	go.starlark.net v0.0.0-20210312235212-74c10e2c17dc
	go.uber.org/multierr v1.6.0 // indirect
	go.uber.org/zap v1.16.0 // indirect
	golang.org/x/mod v0.4.2 // indirect
	golang.org/x/net v0.0.0-20210331212208-0fccb6fa2b5c // indirect
	golang.org/x/sys v0.0.0-20210403161142-5e06dd20ab57 // indirect
	golang.org/x/term v0.0.0-20210317153231-de623e64d2a6 // indirect
	golang.org/x/text v0.3.6 // indirect
	google.golang.org/genproto v0.0.0-20210402141018-6c239bbf2bb1 // indirect
	gopkg.in/yaml.v3 v3.0.0-20210107192922-496545a6307b
	mvdan.cc/sh/v3 v3.3.0-0.dev.0.20210226093739-3d8d47845eeb
)

replace github.com/ngld/knossos/packages/libknossos => ../libknossos

replace github.com/ngld/knossos/packages/libarchive => ../libarchive

replace github.com/ngld/knossos/packages/api => ../api
