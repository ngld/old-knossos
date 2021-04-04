package mods

import (
	"context"
	"encoding/json"
	"os/exec"
	"path/filepath"
	"runtime"

	"github.com/ngld/knossos/packages/api/client"
	"github.com/ngld/knossos/packages/libknossos/pkg/api"
	"github.com/ngld/knossos/packages/libknossos/pkg/storage"
	"github.com/rotisserie/eris"
	"golang.org/x/sys/cpu"
)

type jsonFlags struct {
	Version struct {
		Full        string
		Major       int
		Minor       int
		Build       int
		HasRevision bool `json:"has_revision"`
		Revision    int
		RevisionStr string `json:"revision_str"`
	}

	// easy_flags skipped

	Flags []struct {
		Name        string
		Description string
		FsoOnly     bool `json:"fso_only"`
		// on_flags and off_flags skipped
		Type   string
		WebURL string `json:"web_url"`
	}

	Caps     []string
	Voices   []string
	Displays []struct {
		Index  int
		Name   string
		X      int
		Y      int
		Width  int
		Height int
		Modes  []struct {
			X    int
			Y    int
			Bits int
		}
	}

	Openal struct {
		VersionMajor    int             `json:"version_major"`
		VersionMinor    int             `json:"version_minor"`
		DefaultPlayback string          `json:"default_playback"`
		DefaultCapture  string          `json:"default_capture"`
		PlaybackDevices []string        `json:"playback_devices"`
		CaptureDevices  []string        `json:"capture_devices"`
		EfxSupport      map[string]bool `json:"efx_support"`
	}

	Joysticks []struct {
		Name       string
		GUID       string
		NumAxes    int  `json:"num_axes"`
		NumBalls   int  `json:"num_balls"`
		NumButtons int  `json:"num_buttons"`
		NumHats    int  `json:"num_hats"`
		IsHaptic   bool `json:"is_haptic"`
	}

	PrefPath string `json:"pref_path"`
}

func GetFlagsForMod(ctx context.Context, mod *client.Release) (map[string]*client.FlagInfo_Flag, error) {
	var engine *client.Release

	for modid, version := range mod.DependencySnapshot {
		dep, err := storage.GetMod(ctx, modid, version)
		if err != nil {
			return nil, eris.Wrapf(err, "failed to resolve dependency %s (%s)", modid, version)
		}

		if dep.Type == client.ModType_ENGINE {
			if engine != nil {
				return nil, eris.New("more than one engine dependency")
			}

			engine = dep
		}
	}

	if engine == nil {
		return nil, eris.New("no engine found")
	}

	return GetFlagsForEngine(ctx, engine)
}

func GetFlagsForEngine(ctx context.Context, engine *client.Release) (map[string]*client.FlagInfo_Flag, error) {
	result := make(map[string]*client.FlagInfo_Flag)
	binaryPath, err := getBinaryForEngine(ctx, engine)
	if err != nil {
		return nil, err
	}

	api.Log(ctx, api.LogInfo, "Running \"%s -parse_cmdline_only -get_flags json_v1\"", binaryPath)
	proc := exec.Command(binaryPath, "-parse_cmdline_only", "-get_flags", "json_v1")
	proc.Env = append(proc.Env, "FSO_KEEP_STDOUT=1")
	out, err := proc.CombinedOutput()
	// Ignore the error if it's only about the exit code being 1 because that's normal.
	if err != nil && proc.ProcessState.ExitCode() != 1 {
		return nil, eris.Wrapf(err, "failed to run %s", binaryPath)
	}

	api.Log(ctx, api.LogInfo, "Got: %s", out)
	flags := jsonFlags{}
	err = json.Unmarshal(out, &flags)
	if err != nil {
		return nil, eris.Wrapf(err, "failed to parse output from %s", binaryPath)
	}

	for _, flag := range flags.Flags {
		result[flag.Name] = &client.FlagInfo_Flag{
			Flag:     flag.Name,
			Label:    flag.Description,
			Category: flag.Type,
			Help:     flag.WebURL,
		}
	}

	return result, nil
}

func getBinaryForEngine(ctx context.Context, engine *client.Release) (string, error) {
	binaryScore := uint32(0)
	binaryPath := ""

	for _, pkg := range engine.Packages {
		shouldSkip := false
		for _, spec := range pkg.CpuSpec.GetRequiredFeatures() {
			switch spec {
			case "windows":
				shouldSkip = runtime.GOOS != "windows"
			case "linux":
				shouldSkip = runtime.GOOS != "linux"
			case "macosx":
				shouldSkip = runtime.GOOS != "darwin"
			case "x86_64":
				// TODO make sure that this check yields the correct result even for 32bit builds of Knossos
				shouldSkip = runtime.GOARCH != "amd64"
			case "avx":
				shouldSkip = !cpu.X86.HasAVX
			case "avx2":
				shouldSkip = !cpu.X86.HasAVX2
			case "avx512":
				shouldSkip = !cpu.X86.HasAVX512
			}

			if shouldSkip {
				break
			}
		}

		if shouldSkip {
			continue
		}

		for _, exe := range pkg.Executables {
			if exe.Label == "" && !exe.Debug && exe.Priority > binaryScore {
				binaryScore = exe.Priority
				binaryPath = filepath.Join(engine.Folder, pkg.Folder, exe.Path)
			}
		}
	}

	return binaryPath, nil
}
