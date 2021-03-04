package cmd

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/mitchellh/colorstring"
	"github.com/rotisserie/eris"
	"github.com/rs/zerolog"
)

type ConsoleWriter struct {
	buffer strings.Builder
	lock   sync.Mutex
}

func NewConsoleWriter() *ConsoleWriter {
	return &ConsoleWriter{}
}

func (w *ConsoleWriter) Write(p []byte) (n int, err error) {
	w.lock.Lock()
	defer w.lock.Unlock()

	var evt map[string]interface{}
	d := json.NewDecoder(bytes.NewReader(p))
	d.UseNumber()
	err = d.Decode(&evt)
	if err != nil {
		return n, eris.Wrapf(err, "cannot decode event: %s", p)
	}

	w.buffer.Reset()
	switch evt["level"] {
	case "fatal":
		fallthrough
	case "error":
		w.buffer.WriteString("[red]")
	case "warn":
		w.buffer.WriteString("[yellow]")
	case "debug":
		fallthrough
	case "trace":
		w.buffer.WriteString("[blue]")
	default:
		w.buffer.WriteString("[green]")
	}

	task, ok := evt["task"]
	if ok {
		w.buffer.WriteString(task.(string) + ": ")
	}

	if evt["level"] == "error" {
		w.buffer.WriteString("Error: ")
	}

	msg := evt["message"].(string)

	path, ok := evt["path"]
	if ok {
		// simplify the path
		relPath, err := filepath.Rel(".", path.(string))
		if err == nil {
			msg = strings.ReplaceAll(msg, path.(string), relPath)
		}
	}

	w.buffer.WriteString(msg)

	errorDetails, ok := evt["error"]
	if ok {
		w.buffer.WriteString("\n")
		w.buffer.WriteString(errorDetails.(string))
	}

	if os.Getenv("BUILDSYS_DEBUG") != "" {
		w.buffer.WriteString("\n")
		for name, value := range evt {
			w.buffer.WriteString(fmt.Sprintf("  %s: %+v\n", name, value))
		}
	}

	w.buffer.WriteString("[reset]\n")
	return colorstring.Fprint(os.Stderr, w.buffer.String())
}

func init() {
	zerolog.ErrorMarshalFunc = func(err error) interface{} {
		return eris.ToString(err, os.Getenv("BUILDSYS_DEBUG") != "")
	}
}
