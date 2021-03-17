package twirp

import (
	"context"
	"encoding/base64"
	"io/ioutil"
	"os"
	"path/filepath"

	"github.com/rotisserie/eris"

	pbapi "github.com/ngld/knossos/packages/api/api"
	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
	"github.com/ngld/knossos/packages/libknossos/pkg/mods"
	"github.com/ngld/knossos/packages/libknossos/pkg/storage"
)

func (kn *knossosServer) ScanLocalMods(ctx context.Context, task *client.TaskRequest) (*client.SuccessResponse, error) {
	settings, err := storage.GetSettings(ctx)
	if err != nil {
		return nil, err
	}

	pathQueue := []string{settings.LibraryPath}
	modFiles := []string{}
	for len(pathQueue) > 0 {
		item := pathQueue[0]
		pathQueue = pathQueue[1:]

		info, err := os.Stat(item)
		if err != nil {
			return nil, err
		}

		if !info.IsDir() {
			return nil, eris.Errorf("Tried to scan %s which is not a directory", item)
		}

		subs, err := os.ReadDir(item)
		if err != nil {
			return nil, err
		}
		for _, entry := range subs {
			if entry.IsDir() {
				pathQueue = append(pathQueue, filepath.Join(item, entry.Name()))
			} else if entry.Name() == "mod.json" {
				modFiles = append(modFiles, filepath.Join(item, "mod.json"))
			}
		}
	}

	api.TaskLog(ctx, task.Ref, client.LogMessage_INFO, "Found %d mod.json files. Importing...", len(modFiles))
	err = mods.ImportMods(ctx, modFiles)
	if err != nil {
		return nil, err
	}

	api.TaskLog(ctx, task.Ref, client.LogMessage_INFO, "Done")
	api.SetProgress(ctx, task.Ref, 1, "Done")

	return &client.SuccessResponse{Success: true}, nil
}

func (kn *knossosServer) GetLocalMods(ctx context.Context, _ *client.NullMessage) (*client.SimpleModList, error) {
	modMeta, err := storage.GetSimpleLocalModList(ctx, 0)
	if err != nil {
		return nil, err
	}

	result := new(client.SimpleModList)
	result.Mods = make([]*client.SimpleModList_Item, len(modMeta))
	for idx, mod := range modMeta {
		m := new(client.SimpleModList_Item)
		m.Id = mod.ID
		m.Title = mod.Title
		m.Version = mod.Version
		m.Description = mod.Description

		if mod.Logo != "" {
			content, err := ioutil.ReadFile(mod.Logo)
			if err == nil {
				m.Logo = "data:image/jpeg;base64," + base64.RawStdEncoding.EncodeToString(content)
			} else if !eris.Is(err, os.ErrNotExist) {
				return nil, err
			}
		}

		if mod.Tile != "" {
			content, err := ioutil.ReadFile(mod.Tile)
			if err == nil {
				m.Tile = "data:image/jpeg;base64," + base64.RawStdEncoding.EncodeToString(content)
			} else if !eris.Is(err, os.ErrNotExist) {
				return nil, err
			}
		}

		switch mod.Type {
		case "mod":
			m.Type = pbapi.ModType_MOD
		case "tc":
			m.Type = pbapi.ModType_TOTAL_CONVERSION
		case "engine":
			m.Type = pbapi.ModType_ENGINE
		case "tool":
			m.Type = pbapi.ModType_TOOL
		case "extension":
			m.Type = pbapi.ModType_EXTENSION
		default:
			m.Type = pbapi.ModType_MOD
		}

		switch mod.Stability {
		case "stable":
			m.Stability = pbapi.ReleaseStability_STABLE
		case "rc":
			m.Stability = pbapi.ReleaseStability_RC
		case "nightly":
			m.Stability = pbapi.ReleaseStability_NIGHTLY
		}

		result.Mods[idx] = m
	}

	return result, nil
}
