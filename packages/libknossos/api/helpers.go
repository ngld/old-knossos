package main

import (
	"bytes"
	"net/http"
)

type memoryResponse struct {
	http.ResponseWriter
	headers    http.Header
	resp       *bytes.Buffer
	statusCode int
}

func newMemoryResponse() *memoryResponse {
	return &memoryResponse{
		headers: http.Header{},
		resp:    bytes.NewBuffer([]byte{}),
	}
}

func (r *memoryResponse) Header() http.Header {
	return r.headers
}

func (r *memoryResponse) Write(data []byte) (int, error) {
	return r.resp.Write(data)
}

func (r *memoryResponse) WriteHeader(statusCode int) {
	r.statusCode = statusCode
}
