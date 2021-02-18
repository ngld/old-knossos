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
	"net/http"
	"net/url"
	"strings"
	"unsafe"

	"github.com/ngld/knossos/packages/libknossos/pkg/twirp"
)

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
	server     http.Handler
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
	var err error
	server, err = twirp.NewServer()
	if err != nil {
		log(logError, "Failed to init twirp: %+v", err)
		return false
	}

	return true
}

//KnossosHandleRequest handles an incoming request from CEF
//export KnossosHandleRequest
func KnossosHandleRequest(urlPtr *C.char, urlLen C.int, bodyPtr unsafe.Pointer, bodyLen C.int) *C.KnossosResponse {
	body := C.GoBytes(bodyPtr, bodyLen)
	reqURL, err := url.Parse(C.GoStringN(urlPtr, urlLen))
	if err == nil {
		req := http.Request{
			Method: "POST",
			URL:    reqURL,
			Header: http.Header{
				"Content-Type": []string{"application/protobuf"},
			},
			Body: newByteBufferCloser(body),
		}

		twirpResp := newMemoryResponse()
		server.ServeHTTP(twirpResp, &req)

		resp := C.make_response()
		resp.status_code = C.int(twirpResp.statusCode)
		resp.header_count = C.uint8_t(len(twirpResp.headers))
		resp.headers = C.make_header_array(resp.header_count)

		idx := C.uint8_t(0)
		for k, v := range twirpResp.headers {
			C.set_header(resp.headers, idx, k, strings.Join(v, ", "))
			idx++
		}

		body := twirpResp.resp.Bytes()
		resp.response_data = C.CBytes(body)
		resp.response_length = C.size_t(len(body))

		return resp
	}

	resp := C.make_response()
	resp.status_code = 503
	resp.header_count = 1
	resp.headers = C.make_header_array(1)

	C.set_header(resp.headers, 0, "Content-Type", "text/plain")
	C.set_body(resp, fmt.Sprintf("Error: %+v", err))

	return resp
}

func main() {}
