package main

import (
	"flag"
	"fmt"

	"github.com/ngld/knossos/packages/libarchive"
)

func main() {
	flag.Parse()
	filename := flag.Arg(0)
	if filename == "" {
		fmt.Println("No filename passed")
		return
	}

	archive, err := libarchive.OpenArchive(filename)
	if err != nil {
		panic(err)
	}

	for archive.Next() {
		fmt.Println(archive.Entry.Pathname)
	}

	if archive.Error() != nil {
		panic(archive.Error())
	}

	fmt.Println("Done")
}
