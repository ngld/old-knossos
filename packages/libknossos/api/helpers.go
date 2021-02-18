package main

import (
	"bytes"
	"io"
	"net/http"
)

type byteBufferCloser struct {
	io.ReadCloser
	buffer *bytes.Buffer
}

func newByteBufferCloser(buf []byte) *byteBufferCloser {
	return &byteBufferCloser{
		buffer: bytes.NewBuffer(buf),
	}
}

func (b *byteBufferCloser) Read(p []byte) (n int, err error) {
	return b.buffer.Read(p)
}

func (b *byteBufferCloser) Close() error {
	b.buffer = nil
	return nil
}

type memoryResponse struct {
	http.ResponseWriter
	statusCode int
	headers    http.Header
	resp       *bytes.Buffer
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
