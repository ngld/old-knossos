package main

//#include <stdlib.h>
//#include <stdint.h>
//#include <string.h>
//
//typedef struct {
//	char* header_name;
//  size_t header_len;
//  char* value;
//  size_t value_len;
//} KnossosHeader;
//
//typedef struct {
//  int status_code;
//	void* response_data;
//  size_t response_length;
//  KnossosHeader* headers;
//  uint8_t header_count;
//} KnossosResponse;
//
//typedef void (*KnossosLogCallback)(uint8_t level, char* message, int length);
//
//#ifndef GO_CGO_EXPORT_PROLOGUE_H
//static void call_log_cb(KnossosLogCallback cb, uint8_t level, char* message, int length) {
//	cb(level, message, length);
//}
//
//static KnossosResponse* make_response() {
//  return (KnossosResponse*) malloc(sizeof(KnossosResponse));
//}
//
//static KnossosHeader* make_header_array(uint8_t length) {
//  return (KnossosHeader*) malloc(sizeof(KnossosHeader) * length);
//}
//
//static void set_header(KnossosHeader* harray, uint8_t idx, _GoString_ name, _GoString_ value) {
//  KnossosHeader* hdr = &harray[idx];
//  hdr->header_len = _GoStringLen(name);
//  hdr->header_name = (char*)malloc(hdr->header_len);
//  memcpy(hdr->header_name, _GoStringPtr(name), hdr->header_len);
//
//  hdr->value_len = _GoStringLen(value);
//  hdr->value = (char*)malloc(hdr->value_len);
//  memcpy(hdr->value, _GoStringPtr(value), hdr->value_len);
//}
//
//static void set_body(KnossosResponse* response, _GoString_ body) {
//  response->response_data = (void*)_GoStringPtr(body);
//  response->response_length = _GoStringLen(body);
//}
//
//void KnossosFreeKnossosResponse(KnossosResponse* response) {
//  for (int i = 0; i < response->header_count; i++) {
//    KnossosHeader hdr = response->headers[i];
//    free(hdr.header_name);
//    free(hdr.value);
//  }
//  free(response->headers);
//  free(response);
//}
//#else
//extern void KnossosFreeKnossosResponse(KnossosResponse* response);
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
	"unsafe"
)

type resource struct {
	Handle io.Reader
	URL    string
	Path   string
}

type logLevel C.uint8_t

const (
	logInfo  = logLevel(C.KNOSSOS_LOG_INFO)
	logWarn  = logLevel(C.KNOSSOS_LOG_WARNING)
	logError = logLevel(C.KNOSSOS_LOG_ERROR)
	logFatal = logLevel(C.KNOSSOS_LOG_FATAL)
)

var (
	ready      = false
	staticRoot string
	logCb      C.KnossosLogCallback
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

//KnossosHandleRequest handles an incoming request from CEF
//export KnossosHandleRequest
func KnossosHandleRequest(urlPtr *C.char, urlLen C.size_t, bodyPtr unsafe.Pointer, bodyLen C.size_t) *C.KnossosResponse {
	resp := C.make_response()
	resp.status_code = 200
	resp.header_count = 1
	resp.headers = C.make_header_array(1)

	C.set_header(resp.headers, 0, "Content-Type", "text/plain")
	C.set_body(resp, "Hello World")

	return resp
}

func main() {}
