package twirp

import (
	"context"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"

	"github.com/rotisserie/eris"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
	"github.com/ngld/knossos/packages/libknossos/pkg/mods"
	"github.com/ngld/knossos/packages/libknossos/pkg/storage"
)

func (kn *knossosServer) ScanLocalMods(ctx context.Context, task *client.TaskRequest) (*client.SuccessResponse, error) {
	api.RunTask(ctx, task.Ref, func(ctx context.Context) error {
		settings, err := storage.GetSettings(ctx)
		if err != nil {
			return err
		}

		pathQueue := []string{settings.LibraryPath}
		modFiles := []string{}
		for len(pathQueue) > 0 {
			item := pathQueue[0]
			pathQueue = pathQueue[1:]

			info, err := os.Stat(item)
			if err != nil {
				return err
			}

			if !info.IsDir() {
				return eris.Errorf("Tried to scan %s which is not a directory", item)
			}

			subs, err := os.ReadDir(item)
			if err != nil {
				return err
			}
			for _, entry := range subs {
				if entry.IsDir() {
					pathQueue = append(pathQueue, filepath.Join(item, entry.Name()))
				} else if entry.Name() == "mod.json" {
					modFiles = append(modFiles, filepath.Join(item, "mod.json"))
				}
			}
		}

		api.TaskLog(ctx, client.LogMessage_INFO, "Found %d mod.json files. Importing...", len(modFiles))
		err = mods.ImportMods(ctx, modFiles)
		if err != nil {
			return err
		}

		api.TaskLog(ctx, client.LogMessage_INFO, "Done")
		api.SetProgress(ctx, 1, "Done")
		return nil
	})

	return &client.SuccessResponse{Success: true}, nil
}

func (kn *knossosServer) GetLocalMods(ctx context.Context, _ *client.NullMessage) (*client.SimpleModList, error) {
	modMeta, err := storage.GetLocalMods(ctx, 0)
	if err != nil {
		return nil, err
	}

	allowedFields := map[string]bool{
		"Modid":   true,
		"Title":   true,
		"Version": true,
		"Type":    true,
		"Teaser":  true,
	}

	// Look for fields in client.Release that are not listed above
	typeDesc := reflect.ValueOf(client.Release{}).Type()
	toClear := make([]int, 0)
	for idx := 0; idx < typeDesc.NumField(); idx++ {
		field := typeDesc.Field(idx)
		if field.PkgPath != "" {
			// Skip unexported fields
			continue
		}

		_, good := allowedFields[field.Name]
		if !good {
			toClear = append(toClear, idx)
		}
	}

	for _, mod := range modMeta {
		// Clear all fields listed in toClear to reduce the size of the result
		ref := reflect.ValueOf(mod).Elem()
		for _, fieldIdx := range toClear {
			field := ref.Field(fieldIdx)
			field.Set(reflect.Zero(field.Type()))
		}
	}

	sort.Sort(mods.SortByTitle{ReleaseCollection: modMeta})

	return &client.SimpleModList{
		Mods: modMeta,
	}, nil
}

func (kn *knossosServer) GetModInfo(ctx context.Context, req *client.ModInfoRequest) (*client.ModInfoResponse, error) {
	mod, err := storage.GetMod(ctx, req.Id, req.Version)
	if err != nil {
		return nil, err
	}

	versions, err := storage.GetVersionsForMod(ctx, req.Id)
	if err != nil {
		return nil, err
	}

	mod.Folder = ""
	mod.Packages = make([]*client.Package, 0)

	return &client.ModInfoResponse{
		Mod:      mod,
		Versions: versions,
	}, nil
}

func (kn *knossosServer) GetModDependencies(ctx context.Context, req *client.ModInfoRequest) (*client.ModDependencySnapshot, error) {
	mod, err := storage.GetMod(ctx, req.Id, req.Version)
	if err != nil {
		return nil, err
	}

	versions := make(map[string]*client.ModDependencySnapshot_ModInfo)
	for modID, _ := range mod.DependencySnapshot {
		localVersions, err := storage.GetVersionsForMod(ctx, modID)
		if err != nil {
			return nil, err
		}

		versions[modID] = &client.ModDependencySnapshot_ModInfo{
			Versions: localVersions,
		}
	}

	return &client.ModDependencySnapshot{
		Dependencies: mod.DependencySnapshot,
		Available:    versions,
	}, nil
}

func (kn *knossosServer) GetModFlags(ctx context.Context, req *client.ModInfoRequest) (*client.FlagInfo, error) {
	mod, err := storage.GetMod(ctx, req.Id, req.Version)
	if err != nil {
		return nil, err
	}

	flagInfo, err := mods.GetFlagsForMod(ctx, mod)
	if err != nil {
		return nil, err
	}

	userSettings, err := storage.GetUserSettingsForMod(ctx, req.Id, req.Version)
	if err != nil {
		return nil, err
	}

	cmdline := userSettings.Cmdline
	if cmdline == "" {
		cmdline = mod.Cmdline
	}

	for _, flag := range flagInfo {
		flag.Enabled = strings.Contains(cmdline, flag.Flag)
	}

	return &client.FlagInfo{
		Flags: flagInfo,
	}, nil
}
