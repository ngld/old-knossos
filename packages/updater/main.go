package main

import (
	"fmt"
	"time"

	"github.com/ngld/knossos/packages/libarchive"
	"github.com/ngld/knossos/packages/updater/ui"
)

func main() {
	go func() {
		ui.Log(ui.LogInfo, "Version: %d", libarchive.Version())
		for idx := 0; idx < 10; idx++ {
			ui.SetProgress(float32(idx)/10, fmt.Sprintf("Countdown %d", 10-idx))
			time.Sleep(1 * time.Second)
		}
	}()

	err := ui.RunApp("Knossos Updater", 900, 500)
	if err != nil {
		panic(err)
	}
}
