package twirp

import (
	"context"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"github.com/rotisserie/eris"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
)

func Download(ctx context.Context, step api.TaskStep, url string, dest io.Writer) error {
	download, err := http.Get(url)
	if err != nil {
		return eris.Wrapf(err, "Failed download of %s", url)
	}
	defer download.Body.Close()

	if download.StatusCode != 200 {
		return eris.Wrapf(err, "Download of %s failed with status %d", url, download.StatusCode)
	}

	_, err = api.ProgressCopier(ctx, step, download.ContentLength, download.Body, dest)
	if err != nil {
		return eris.Wrapf(err, "Download of %s failed", url)
	}

	return nil
}

func (kn *knossosServer) SpeedTest(ctx context.Context, req *client.TaskRequest) (*client.SpeedTestResult, error) {
	api.RunTask(ctx, req.Ref, func(c context.Context) error {
		api.TaskLog(ctx, client.LogMessage_INFO, "Starting test")

		download, err := http.Get("https://cf.fsnebula.org/storage/big")
		if err != nil {
			return eris.Wrap(err, "Failed speed test for cf.fsnebula.org")
		}
		defer download.Body.Close()

		api.TaskLog(ctx, client.LogMessage_INFO, "Got status %d", download.StatusCode)
		if download.StatusCode != 200 {
			api.TaskLog(ctx, client.LogMessage_ERROR, "Download failed (status %d)", download.StatusCode)
			return eris.Errorf("Download from cf.fsnebula.org failed with status %d.", download.StatusCode)
		}

		destPath := filepath.Join(api.SettingsPath(ctx), "dl_dest")
		dest, err := os.Create(destPath)
		if err != nil {
			return eris.Wrap(err, "Failed to create destination file")
		}
		defer func() {
			dest.Close()
			os.Remove(destPath)
		}()

		step := api.TaskStep{
			From:        0,
			To:          0.3,
			Description: "Testing cf.fsnebula.org",
		}

		cfSpeed, err := api.ProgressCopier(ctx, step, download.ContentLength, download.Body, dest)
		if err != nil {
			return eris.Wrap(err, "Failed CF download")
		}
		download.Body.Close()
		dest.Seek(0, io.SeekStart)

		api.TaskLog(ctx, client.LogMessage_INFO, "Starting DL test")
		download, err = http.Get("https://dl.fsnebula.org/storage/big")
		if err != nil {
			return eris.Wrap(err, "Failed speed test for dl.fsnebula.org")
		}

		api.TaskLog(ctx, client.LogMessage_INFO, "Got status %d", download.StatusCode)
		if download.StatusCode != 200 {
			return eris.Errorf("Download from cf.fsnebula.org failed with status %d.", download.StatusCode)
		}

		step.From = 0.3
		step.To = 0.6
		step.Description = "Testing dl.fsnebula.org"
		dlCtx, _ := context.WithTimeout(ctx, 30*time.Second)
		dlSpeed, err := api.ProgressCopier(dlCtx, step, download.ContentLength, download.Body, dest)
		if err != nil {
			return eris.Wrap(err, "Failed DL download")
		}
		download.Body.Close()
		dest.Seek(0, io.SeekStart)

		api.TaskLog(ctx, client.LogMessage_INFO, "Starting discovery test")
		download, err = http.Get("https://aigaion.feralhosting.com/discovery/nebula/big")
		if err != nil {
			return eris.Wrap(err, "Failed discovery download")
		}

		api.TaskLog(ctx, client.LogMessage_INFO, "Got status %d", download.StatusCode)
		if download.StatusCode != 200 {
			return eris.Errorf("Download from aigaion.feralhosting.com failed with status %d.", download.StatusCode)
		}

		step.From = 0.6
		step.To = 1
		step.Description = "Testing aigaion.feralhosting.com"
		disSpeed, err := api.ProgressCopier(ctx, step, download.ContentLength, download.Body, dest)
		if err != nil {
			return eris.Wrap(err, "Failed discovery download")
		}
		dest.Close()

		api.Log(ctx, api.LogInfo, "cf.fsnebula.org: %d", cfSpeed)
		api.Log(ctx, api.LogInfo, "dl.fsnebula.org: %d", dlSpeed)
		api.Log(ctx, api.LogInfo, "aigaion.feralhosting.com: %d", disSpeed)

		return nil
	})
	return &client.SpeedTestResult{}, nil
}
