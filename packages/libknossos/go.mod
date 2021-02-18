module github.com/ngld/knossos/packages/libknossos

go 1.15

require (
	github.com/ngld/knossos/packages/api v0.0.0-00010101000000-000000000000
	github.com/rotisserie/eris v0.5.0
)

replace github.com/ngld/knossos/packages/api => ../api
