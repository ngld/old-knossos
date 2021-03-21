module github.com/ngld/knossos/packages/libknossos

go 1.15

require (
	github.com/DataDog/zstd v1.4.8 // indirect
	github.com/Masterminds/semver/v3 v3.1.1
	github.com/dgraph-io/badger/v3 v3.2011.1
	github.com/golang/protobuf v1.5.1 // indirect
	github.com/golang/snappy v0.0.3 // indirect
	github.com/ngld/knossos/packages/api v0.0.0-00010101000000-000000000000
	github.com/ngld/knossos/packages/libarchive v0.0.0-00010101000000-000000000000
	github.com/rotisserie/eris v0.5.0
	github.com/twitchtv/twirp v7.1.1+incompatible // indirect
	go.opencensus.io v0.23.0 // indirect
	golang.org/x/net v0.0.0-20210316092652-d523dce5a7f4 // indirect
	golang.org/x/sys v0.0.0-20210320140829-1e4c9ba3b0c4 // indirect
	google.golang.org/protobuf v1.26.0
)

replace github.com/ngld/knossos/packages/api => ../api

replace github.com/ngld/knossos/packages/libarchive => ../libarchive
