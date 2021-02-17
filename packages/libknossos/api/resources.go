package main

//#include <stdint.h>
//
//typedef void (*KnossosLogCallback)(uint8_t level, char* message, int length);
//
//#ifndef GO_CGO_EXPORT_PROLOGUE_H
//static void call_log_cb(KnossosLogCallback cb, uint8_t level, char* message, int length) {
//	cb(level, message, length);
//}
//#endif
//
//#define KNOSSOS_LOG_INFO 1
//#define KNOSSOS_LOG_WARNING 2
//#define KNOSSOS_LOG_ERROR 3
//#define KNOSSOS_LOG_FATAL 4
import "C"

import (
	"fmt"
	"io"
	"path/filepath"
	"strings"
)

type resourceType int8

const (
	fileType resourceType = iota + 1
	apiType
)

type resource struct {
	Handle io.Reader
	URL    string
	Path   string
	Type   resourceType
}

type logLevel C.uint8_t

const (
	logInfo  = logLevel(C.KNOSSOS_LOG_INFO)
	logWarn  = logLevel(C.KNOSSOS_LOG_WARNING)
	logError = logLevel(C.KNOSSOS_LOG_ERROR)
	logFatal = logLevel(C.KNOSSOS_LOG_FATAL)
)

var (
	ready         = false
	staticRoot    string
	logCb         C.KnossosLogCallback
	handleCounter = C.uint16_t(1)
	memPool       = map[C.uint16_t]*resource{}
)

func log(level logLevel, msg string, args ...interface{}) {
	finalMsg := fmt.Sprintf(msg, args...)
	C.call_log_cb(logCb, C.uint8_t(level), C.CString(finalMsg), C.int(len(finalMsg)))
}

//KnossosInit has to be called exactly once before calling any other exported function.
//export KnossosInit
func KnossosInit(staticRootChars *C.char, staticRootLen C.int, logFunc C.KnossosLogCallback) bool {
	staticRoot = C.GoStringN(staticRootChars, staticRootLen)
	logCb = logFunc
	ready = true

	return true
}

//KnossosShouldHandleResource returns true if the passed URL is handled by this module
//export KnossosShouldHandleResource
func KnossosShouldHandleResource(urlPtr *C.char, urlLen C.size_t) C.uint16_t {
	if !ready {
		log(logFatal, "KnossosShouldHandleResource called before KnossosInit!")
		return 0
	}

	url := C.GoStringN(urlPtr, C.int(urlLen))
	info := new(resource)
	info.URL = url

	if strings.HasPrefix(url, "https://files.client.fsnebula.org/") {
		info.Type = fileType
		info.Path = filepath.Join(staticRoot, url[34:])
	}

	if strings.HasPrefix(url, "https://api.client.fsnebula.org/") {
		info.Type = apiType
		info.Path = url[32:]
	}

	handle := handleCounter
	handleCounter++
	memPool[handle] = info
	return C.uint16_t(handle)
}

//KnossosGetResourceSize returns the expected resource size or -1 if it's unknown.
//export KnossosGetResourceSize
func KnossosGetResourceSize(handle C.uint16_t) C.int {
	if !ready {
		log(logFatal, "KnossosGetResourceSize called before KnossosInit!")
		return 0
	}

	_, found := memPool[handle]
	if !found {
		log(logFatal, "KnossosGetResourceSize called with invalid handle")
		return 0
	}

	return 1
}

//KnossosFree should be called once a resource pointer isn't needed anymore
//export KnossosFree
func KnossosFree(handle C.uint16_t) {
	log(logLevel(logInfo), "Freeing request for %s", memPool[handle].URL)
	delete(memPool, handle)
}

func main() {}
