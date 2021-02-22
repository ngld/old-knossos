package twirp

import (
	"context"
	"net/http"
	"runtime"
	"time"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
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

func (kn *knossosServer) DispatchTest(ctx context.Context, _ *client.NullMessage) (*client.NullResponse, error) {
	api.Log(ctx, api.LogInfo, "Starting countdown...")
	api.DispatchMessage(ctx, &client.ClientSentEvent{
		Ref: 1,
		Payload: &client.ClientSentEvent_Message{
			Message: &client.LogMessage{
				Level: client.LogMessage_INFO, Message: "Start!",
			},
		},
	})

	time.Sleep(time.Second * 1)

	api.Log(ctx, api.LogInfo, "1...")
	api.DispatchMessage(ctx, &client.ClientSentEvent{
		Ref: 1,
		Payload: &client.ClientSentEvent_Message{
			Message: &client.LogMessage{
				Level: client.LogMessage_INFO, Message: "1",
			},
		},
	})

	time.Sleep(time.Second * 1)

	api.Log(ctx, api.LogInfo, "2...")
	api.DispatchMessage(ctx, &client.ClientSentEvent{
		Ref: 1,
		Payload: &client.ClientSentEvent_Message{
			Message: &client.LogMessage{
				Level: client.LogMessage_INFO, Message: "2",
			},
		},
	})

	time.Sleep(time.Second * 1)

	api.Log(ctx, api.LogInfo, "3!")
	api.DispatchMessage(ctx, &client.ClientSentEvent{
		Ref: 1,
		Payload: &client.ClientSentEvent_Message{
			Message: &client.LogMessage{
				Level: client.LogMessage_INFO, Message: "3",
			},
		},
	})

	return &client.NullResponse{
		Dummy: true,
	}, nil
}
