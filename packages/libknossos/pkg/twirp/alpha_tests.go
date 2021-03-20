package twirp

import (
	"context"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/rotisserie/eris"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libarchive"
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
	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Starting test")

	download, err := http.Get("https://cf.fsnebula.org/storage/big")
	if err != nil {
		return nil, eris.Wrap(err, "Failed speed test for cf.fsnebula.org")
	}
	defer download.Body.Close()

	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Got status %d", download.StatusCode)
	if download.StatusCode != 200 {
		api.TaskLog(ctx, req.Ref, client.LogMessage_ERROR, "Download failed (status %d)", download.StatusCode)
		return nil, eris.Errorf("Download from cf.fsnebula.org failed with status %d.", download.StatusCode)
	}

	destPath := filepath.Join(api.SettingsPath(ctx), "dl_dest")
	dest, err := os.Create(destPath)
	if err != nil {
		return nil, eris.Wrap(err, "Failed to create destination file")
	}
	defer func() {
		dest.Close()
		os.Remove(destPath)
	}()

	step := api.TaskStep{
		Ref:         req.Ref,
		From:        0,
		To:          0.3,
		Description: "Testing cf.fsnebula.org",
	}

	cfSpeed, err := api.ProgressCopier(ctx, step, download.ContentLength, download.Body, dest)
	if err != nil {
		return nil, eris.Wrap(err, "Failed CF download")
	}
	download.Body.Close()
	dest.Seek(0, io.SeekStart)

	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Starting DL test")
	download, err = http.Get("https://dl.fsnebula.org/storage/big")
	if err != nil {
		return nil, eris.Wrap(err, "Failed speed test for dl.fsnebula.org")
	}

	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Got status %d", download.StatusCode)
	if download.StatusCode != 200 {
		return nil, eris.Errorf("Download from cf.fsnebula.org failed with status %d.", download.StatusCode)
	}

	step.From = 0.3
	step.To = 0.6
	step.Description = "Testing dl.fsnebula.org"
	dlCtx, _ := context.WithTimeout(ctx, 30*time.Second)
	dlSpeed, err := api.ProgressCopier(dlCtx, step, download.ContentLength, download.Body, dest)
	if err != nil {
		return nil, eris.Wrap(err, "Failed DL download")
	}
	download.Body.Close()
	dest.Seek(0, io.SeekStart)

	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Starting discovery test")
	download, err = http.Get("https://aigaion.feralhosting.com/discovery/nebula/big")
	if err != nil {
		return nil, eris.Wrap(err, "Failed discovery download")
	}

	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Got status %d", download.StatusCode)
	if download.StatusCode != 200 {
		return nil, eris.Errorf("Download from aigaion.feralhosting.com failed with status %d.", download.StatusCode)
	}

	step.From = 0.6
	step.To = 1
	step.Description = "Testing aigaion.feralhosting.com"
	disSpeed, err := api.ProgressCopier(ctx, step, download.ContentLength, download.Body, dest)
	if err != nil {
		return nil, eris.Wrap(err, "Failed discovery download")
	}
	dest.Close()

	return &client.SpeedTestResult{Speeds: map[string]uint32{
		"cf.fsnebula.org":          uint32(cfSpeed),
		"dl.fsnebula.org":          uint32(dlSpeed),
		"aigaion.feralhosting.com": uint32(disSpeed),
	}}, nil
}

func (kn *knossosServer) ArchiveTest(ctx context.Context, req *client.TaskRequest) (*client.NullResponse, error) {
	api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "Downloading test archive")

	api.Log(ctx, api.LogInfo, "libarchive version: %d", libarchive.Version())

	destPath := filepath.Join(api.SettingsPath(ctx), "test_archive.7z")
	defer os.Remove(destPath)

	files := []string{
		"https://cf.fsnebula.org/storage/cb/db/833e5d69d7fe7a6c4bf1f7d64096a86cd1a8faab48c17d187f8155ae5189/rn/core.7z",
		"https://github.com/scp-fs2open/fs2open.github.com/releases/download/release_21_0_0/fs2_open_21_0_0-builds-x64-AVX.zip",
	}

	for idx, url := range files {
		step := api.TaskStep{
			Ref:         req.Ref,
			From:        float32(idx) / float32(len(files)),
			To:          float32(idx+1) / float32(len(files)),
			Description: "Downloading",
		}

		dest, err := os.Create(destPath)
		if err != nil {
			return nil, eris.Wrapf(err, "Failed to create %s", destPath)
		}

		err = Download(ctx, step, url, dest)
		if err != nil {
			dest.Close()
			return nil, eris.Wrap(err, "Failed to download test archive")
		}
		dest.Close()

		archive, err := libarchive.OpenArchive(destPath)
		if err != nil {
			return nil, eris.Wrap(err, "Failed to open test archive")
		}

		api.Log(ctx, api.LogInfo, "%+v", archive.Error())

		buffer := make([]byte, 1024)
		for archive.Next() {
			api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "File: %s", archive.Entry.Pathname)
			if strings.HasSuffix(archive.Entry.Pathname, ".tbm") {
				read, _ := archive.Read(buffer)
				api.TaskLog(ctx, req.Ref, client.LogMessage_INFO, "First 1K: %s", string(buffer[:read]))
			}
		}
		archive.Close()
	}

	return &client.NullResponse{}, nil
}
