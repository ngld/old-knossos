package twirp

import (
	"context"
	"net/http"
	"runtime"

	"github.com/ngld/knossos/packages/api/client"
)

type knossosServer struct {
	client.Knossos
}

func NewServer() (http.Handler, error) {
	return client.NewKnossosServer(&knossosServer{}), nil
}

func (kn *knossosServer) Wakeup(context.Context, *client.NullMessage) (*client.WakeupResponse, error) {
	return &client.WakeupResponse{
		Success: true,
		Version: "0.0.0",
		Os:      runtime.GOOS,
	}, nil
}
