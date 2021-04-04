package mods

import (
	"bytes"
	"context"
	"encoding/hex"
	"encoding/json"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/aidarkhanov/nanoid"
	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
	"github.com/ngld/knossos/packages/libknossos/pkg/storage"
	"github.com/rotisserie/eris"
	"google.golang.org/protobuf/types/known/timestamppb"
)

type KnDep struct {
	ID       string
	Version  string
	Packages []string
}

type KnExe struct {
	File       string
	Label      string
	Properties struct {
		X64  bool
		SSE2 bool
		AVX  bool
		AVX2 bool
	}
}

type KnChecksum [2]string

type KnArchive struct {
	Checksum KnChecksum
	Filename string
	Dest     string
	URLs     []string
	FileSize int
}

type KnFile struct {
	Filename string
	Archive  string
	OrigName string
	Checksum KnChecksum
}

type KnPackage struct {
	Name         string
	Notes        string
	Status       string
	Environment  string
	Folder       string
	Dependencies []KnDep
	Executables  []KnExe
	Files        []KnArchive
	Filelist     []KnFile
	IsVp         bool
}

type KnMod struct {
	LocalPath     string
	Title         string
	Version       string
	Parent        string
	Stability     string
	Description   string
	Logo          string
	Tile          string
	Banner        string
	ReleaseThread string `json:"release_thread"`
	Type          string
	ID            string
	Notes         string
	Folder        string
	FirstRelease  string `json:"first_release"`
	LastUpdate    string `json:"last_update"`
	Cmdline       string
	ModFlag       []string `json:"mod_flag"`
	DevMode       bool     `json:"dev_mode"`
	Screenshots   []string
	Packages      []KnPackage
	Videos        []string
}

type UserModSettings struct {
	Cmdline     string
	CustomBuild string `json:"custom_build"`
	LastPlayed  string `json:"last_played"`
	Exe         []string
}

func convertPath(ctx context.Context, modPath, input string) *client.FileRef {
	if input == "" {
		return nil
	}

	ref := &client.FileRef{
		Fileid: "local_" + nanoid.New(),
		Urls:   []string{"file://" + filepath.ToSlash(filepath.Join(modPath, input))},
	}
	storage.ImportFile(ctx, ref)

	return ref
}

func convertChecksum(input KnChecksum) (*client.Checksum, error) {
	digest, err := hex.DecodeString(input[1])
	if err != nil {
		return nil, err
	}

	return &client.Checksum{
		Algo:   input[0],
		Digest: digest,
	}, nil
}

func cleanEmptyFolders(ctx context.Context, folder string) error {
	items, err := os.ReadDir(folder)
	if err != nil {
		return err
	}

	for _, item := range items {
		if item.IsDir() {
			err = cleanEmptyFolders(ctx, filepath.Join(folder, item.Name()))
			if err != nil {
				return err
			}
		}
	}

	// Check again because the previous loop might have deleted all remaining folders
	items, err = os.ReadDir(folder)
	if err != nil {
		return err
	}

	if len(items) == 0 {
		return os.Remove(folder)
	}

	return nil
}

func ImportMods(ctx context.Context, modFiles []string) error {
	releases := make([]*client.Release, 0)

	api.Log(ctx, api.LogInfo, "Parsing mod.json files")
	api.SetProgress(ctx, 0, "Processing mods")
	modCount := float32(len(modFiles))

	err := storage.ImportMods(ctx, func(ctx context.Context, importMod func(*client.Release) error) error {
		done := float32(0)
		for _, modFile := range modFiles {
			data, err := ioutil.ReadFile(modFile)
			if err != nil {
				return err
			}

			var mod KnMod
			err = json.Unmarshal(data, &mod)
			if err != nil {
				return err
			}

			modPath, err := filepath.Abs(filepath.Dir(modFile))
			if err != nil {
				return err
			}

			api.SetProgress(ctx, done/modCount, mod.Title+" "+mod.Version)
			done++

			if !mod.DevMode {
				api.Log(ctx, api.LogInfo, "Converting folder structure to dev mode for %s %s", mod.Title, mod.Version)
				workPath := filepath.Join(modPath, "__dev_work")
				err := os.Mkdir(workPath, 0770)
				if err != nil {
					return eris.Wrapf(err, "failed to create working directory %s", workPath)
				}

				items, err := os.ReadDir(modPath)
				if err != nil {
					return err
				}

				// Move all items in the mod into the work subfolder to avoid conflicts between package folders and already
				// existing folders. For example, a package folder named "data" containing a data directory would require
				// this case.
				for _, item := range items {
					if item.Name() != "__dev_work" {
						err = os.Rename(filepath.Join(modPath, item.Name()), filepath.Join(workPath, item.Name()))
						if err != nil {
							return err
						}
					}
				}

				for _, pkg := range mod.Packages {
					pkgPath := filepath.Join(modPath, pkg.Folder)
					err = os.Mkdir(pkgPath, 0770)
					if err != nil && !eris.Is(err, os.ErrExist) {
						return eris.Wrapf(err, "failed to create folder for package %s (%s)", pkg.Name, pkg.Folder)
					}

					for _, pkgFile := range pkg.Filelist {
						src := filepath.Join(workPath, pkgFile.Filename)
						dest := filepath.Join(pkgPath, pkgFile.Filename)
						destParent := filepath.Dir(dest)

						err = os.MkdirAll(destParent, 0770)
						if err != nil {
							relPath, suberr := filepath.Rel(modPath, dest)
							if suberr != nil {
								relPath = dest
							}
							return eris.Wrapf(err, "failed to create folder file %s in package %s", relPath, pkg.Name)
						}

						err = os.Rename(src, dest)
						if err != nil {
							return eris.Wrapf(err, "failed to move %s to %s", src, dest)
						}
					}
				}

				api.Log(ctx, api.LogInfo, "Cleaning up")
				err = cleanEmptyFolders(ctx, workPath)
				if err != nil {
					return eris.Wrap(err, "failed cleanup")
				}

				leftOvers, err := os.ReadDir(workPath)
				if err != nil {
					if !eris.Is(err, os.ErrNotExist) {
						return eris.Wrap(err, "failed to check work folder")
					}
				} else {
					// Move left overs back to mod folder and remove work folder
					for _, item := range leftOvers {
						src := filepath.Join(workPath, item.Name())
						dest := filepath.Join(modPath, item.Name())
						err = os.Rename(src, dest)
						if err != nil {
							return eris.Wrapf(err, "failed to move %s back to %s", src, dest)
						}
					}

					err = os.Remove(workPath)
					if err != nil {
						return eris.Wrapf(err, "failed to remove work folder %s", workPath)
					}
				}

				data = bytes.Replace(data, []byte(`"dev_mode": false,`), []byte(`"dev_mode": true,`), 1)
				err = os.WriteFile(modFile, data, 0660)
				if err != nil {
					return eris.Wrapf(err, "failed to update dev_mode field in %s", modFile)
				}

				api.Log(ctx, api.LogInfo, "Folder conversion done")
			}

			item := new(client.Release)
			item.Modid = mod.ID
			item.Version = mod.Version
			item.Folder = modPath
			item.Title = mod.Title
			item.Description = mod.Description
			item.Teaser = convertPath(ctx, modPath, mod.Tile)
			item.Banner = convertPath(ctx, modPath, mod.Banner)
			item.ReleaseThread = mod.ReleaseThread
			item.Videos = mod.Videos
			item.Notes = mod.Notes
			item.Cmdline = mod.Cmdline
			item.ModOrder = mod.ModFlag

			releases = append(releases, item)

			if mod.FirstRelease != "" {
				releaseDate, err := time.Parse("2006-01-02", mod.FirstRelease)
				if err != nil {
					return err
				}

				item.Released = &timestamppb.Timestamp{
					Seconds: releaseDate.Unix(),
				}
			}

			if mod.LastUpdate != "" {
				updateDate, err := time.Parse("2006-01-02", mod.LastUpdate)
				if err != nil {
					return err
				}

				item.Updated = &timestamppb.Timestamp{
					Seconds: updateDate.Unix(),
				}
			}

			switch mod.Type {
			case "mod":
				item.Type = client.ModType_MOD
			case "tc":
				item.Type = client.ModType_TOTAL_CONVERSION
			case "engine":
				item.Type = client.ModType_ENGINE
			case "tool":
				item.Type = client.ModType_TOOL
			case "extension":
				item.Type = client.ModType_EXTENSION
			default:
				item.Type = client.ModType_MOD
			}

			if item.Type == client.ModType_ENGINE {
				switch mod.Stability {
				case "stable":
					item.Stability = client.ReleaseStability_STABLE
				case "rc":
					item.Stability = client.ReleaseStability_RC
				case "nightly":
					item.Stability = client.ReleaseStability_NIGHTLY
				}
			}

			for _, screen := range mod.Screenshots {
				item.Screenshots = append(item.Screenshots, convertPath(ctx, modPath, screen))
			}

			item.Packages = make([]*client.Package, len(mod.Packages))
			for pIdx, pkg := range mod.Packages {
				pbPkg := new(client.Package)
				pbPkg.Name = pkg.Name
				pbPkg.Folder = pkg.Folder
				pbPkg.Notes = pkg.Notes
				pbPkg.KnossosVp = pkg.IsVp

				switch pkg.Status {
				case "required":
					pbPkg.Type = client.PackageType_REQUIRED
				case "recommended":
					pbPkg.Type = client.PackageType_RECOMMENDED
				case "optional":
					pbPkg.Type = client.PackageType_OPTIONAL
				}

				// TODO: CpuSpec

				pbPkg.Dependencies = make([]*client.Dependency, len(pkg.Dependencies))
				for dIdx, dep := range pkg.Dependencies {
					pbDep := new(client.Dependency)
					pbDep.Modid = dep.ID
					pbDep.Constraint = dep.Version
					pbDep.Packages = dep.Packages
					pbPkg.Dependencies[dIdx] = pbDep
				}

				pbPkg.Archives = make([]*client.PackageArchive, len(pkg.Files))
				for aIdx, archive := range pkg.Files {
					pbArchive := new(client.PackageArchive)
					pbArchive.Id = archive.Filename
					pbArchive.Label = archive.Filename
					pbArchive.Destination = archive.Dest

					chk, err := convertChecksum(archive.Checksum)
					if err != nil {
						return err
					}
					pbArchive.Checksum = chk
					pbArchive.Filesize = uint64(archive.FileSize)
					pbArchive.Download = &client.FileRef{
						Fileid: "local_" + nanoid.New(),
						Urls:   archive.URLs,
					}

					pbPkg.Archives[aIdx] = pbArchive
				}

				pbPkg.Files = make([]*client.PackageFile, len(pkg.Filelist))
				for fIdx, file := range pkg.Filelist {
					pbFile := new(client.PackageFile)
					pbFile.Path = file.Filename
					pbFile.Archive = file.Archive
					pbFile.ArchivePath = file.OrigName

					chk, err := convertChecksum(file.Checksum)
					if err != nil {
						return err
					}
					pbFile.Checksum = chk
					pbPkg.Files[fIdx] = pbFile
				}

				pbPkg.Executables = make([]*client.EngineExecutable, len(pkg.Executables))
				for eIdx, exe := range pkg.Executables {
					pbExe := new(client.EngineExecutable)
					pbExe.Path = exe.File
					pbExe.Label = exe.Label

					prio := uint32(0)
					// See https://github.com/ngld/knossos/blob/1f60d925498c02d3db76a54d3ee20c31b75c5a21/knossos/repo.py#L35-L40
					if exe.Properties.X64 {
						prio += 50
					}
					if exe.Properties.AVX2 {
						prio += 3
					}
					if exe.Properties.AVX {
						prio += 2
					}
					if exe.Properties.SSE2 {
						prio++
					}
					pbExe.Priority = prio
					pbExe.Debug = strings.Contains(strings.ToLower(exe.Label), "debug")
					pbPkg.Executables[eIdx] = pbExe
				}

				item.Packages[pIdx] = pbPkg
			}

			err = importMod(item)
			if err != nil {
				return err
			}
		}

		return nil
	})
	if err != nil {
		return err
	}

	api.Log(ctx, api.LogInfo, "Building dependency snapshots")
	err = storage.BatchUpdate(ctx, func(ctx context.Context) error {
		for _, rel := range releases {
			snapshot, err := GetDependencySnapshot(ctx, storage.LocalMods{}, rel)
			if err != nil {
				api.Log(ctx, api.LogError, "failed to build snapshot for %s (%s): %+v", rel.Modid, rel.Version, err)
				continue
			}

			rel.DependencySnapshot = snapshot
			err = storage.SaveLocalMod(ctx, rel)
			if err != nil {
				return err
			}
		}

		return nil
	})
	if err != nil {
		return err
	}

	api.Log(ctx, api.LogInfo, "Importing user settings")
	return storage.ImportUserSettings(ctx, func(ctx context.Context, importSettings func(string, string, *client.UserSettings) error) error {
		for _, rel := range releases {
			settingsPath := filepath.Join(rel.Folder, "user.json")
			data, err := ioutil.ReadFile(settingsPath)
			if err != nil {
				if !eris.Is(err, os.ErrNotExist) {
					api.Log(ctx, api.LogError, "failed to open %s: %+v", settingsPath, err)
				}
				continue
			}

			var settings UserModSettings
			err = json.Unmarshal(data, &settings)
			if err != nil {
				api.Log(ctx, api.LogError, "failed to parse %s: %+v", settingsPath, err)
				continue
			}

			newSettings := new(client.UserSettings)
			newSettings.Cmdline = settings.Cmdline
			newSettings.CustomBuild = settings.CustomBuild

			if settings.LastPlayed != "" {
				lastPlayed, err := time.Parse("2006-01-02 15:04:05", settings.LastPlayed)
				if err != nil {
					api.Log(ctx, api.LogWarn, "failed to parse last played date in %s: %+v", settingsPath, err)
				} else {
					newSettings.LastPlayed = &timestamppb.Timestamp{
						Seconds: lastPlayed.Unix(),
					}
				}
			}

			if len(settings.Exe) != 0 {
				if len(settings.Exe) != 2 {
					api.Log(ctx, api.LogWarn, "failed to parse selected build in %s: expected two values but found %+v", settingsPath, settings.Exe)
				} else {
					newSettings.EngineOptions = &client.UserSettings_EngineOptions{
						Modid:   settings.Exe[0],
						Version: settings.Exe[1],
					}
				}
			}

			importSettings(rel.Modid, rel.Version, newSettings)
		}

		return nil
	})
}
