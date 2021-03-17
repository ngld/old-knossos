package mods

import (
	"context"
	"encoding/json"
	"io/ioutil"
	"path/filepath"

	"github.com/ngld/knossos/packages/libknossos/pkg/storage"
)

func ImportMods(ctx context.Context, modFiles []string) error {
	mod := storage.KnMod{}
	return storage.ImportMods(ctx, func(importMod func(*storage.KnMod) error) error {
		for _, modFile := range modFiles {
			data, err := ioutil.ReadFile(modFile)
			if err != nil {
				return err
			}

			err = json.Unmarshal(data, &mod)
			if err != nil {
				return err
			}

			modPath, err := filepath.Abs(filepath.Dir(modFile))
			if err != nil {
				return err
			}
			mod.LocalPath = modPath
			if mod.Tile != "" {
				mod.Tile = filepath.Join(modPath, mod.Tile)
			}
			if mod.Logo != "" {
				mod.Logo = filepath.Join(modPath, mod.Logo)
			}
			if mod.Banner != "" {
				mod.Banner = filepath.Join(modPath, mod.Banner)
			}
			for idx, item := range mod.Screenshots {
				mod.Screenshots[idx] = filepath.Join(modPath, item)
			}

			err = importMod(&mod)
			if err != nil {
				return err
			}
		}

		return nil
	})
}
