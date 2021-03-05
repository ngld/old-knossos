# Packages

* api  
  This package contains the various Protobuf definitions for cross-package communication
  (client <-> server and JavaScript <-> Go).
* build-tools  
  This package contains a Go program that's used extensively during the compilation.
  You can run `.tools/tool -h` to get an overview of the implemented commands.
* client  
  The client foundation. It's implemented in C++ and is responsible for connecting
  client-ui and libknossos. It's a fairly thin wrapper around CEF which does the
  heavy lifting.
* client-ui  
  The web interface bundled with client and displayed on start. Implemented in
  TypeScript, CSS and HTML. Interacts with libknossos to perform the actual mod
  installation, etc.
* front  
  Nebula's web interface. Similar to client-ui but it's a real web page that has
  to run in a browser.
* libarchive  
  Build scripts for libarchive. We use that library in libknossos to handle all
  supported archives.
* libknossos  
  The core client-side logic. Implemented in Go. It handles mod downloads,
  archive extraction, checksum verification, etc.
* server  
  The server-side logic. Implemented in Go. This package mostly handles requests
  from front and delivers information from the database or updates the database.
