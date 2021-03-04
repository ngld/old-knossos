package cmd

import (
	"archive/tar"
	"archive/zip"
	"compress/bzip2"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"strings"
	"time"

	"github.com/rotisserie/eris"
	"github.com/schollz/progressbar/v3"
	"github.com/spf13/cobra"
	"github.com/ulikunitz/xz"
	"gopkg.in/yaml.v3"

	"github.com/ngld/knossos/packages/build-tools/pkg"
)

type depSpec struct {
	Condition  string `yaml:"if,omitempty"`
	Rejections string `yaml:"ifNot,omitempty"`
	URL        string
	Dest       string
	Sha256     string
	Strip      int
	MarkExec   []string `yaml:"markExec,omitempty"`
}

type depConfig struct {
	Vars map[string]string
	Deps map[string]depSpec
}

var fetchDepsCmd = &cobra.Command{
	Use:   "fetch-deps",
	Short: "Downloads and unpacks dependencies",
	Long:  `Downloads and unnpacks the dependencies listed in packages/build-tools/DEPS.yml`,
	RunE: func(cmd *cobra.Command, args []string) error {
		pkg.PrintTask("Loading config")
		root, err := pkg.GetProjectRoot()
		if err != nil {
			return err
		}

		cfg, cfgData, stamps, err := getConfig(root)
		if err != nil {
			return err
		}

		pkg.PrintTask("Downloading dependencies")
		err = downloadAndExtract(cmd, cfg, cfgData, stamps, root)
		stampPath := filepath.Join(root, "packages", "build-tools", "DEPS.stamps")
		stampData, jErr := json.Marshal(stamps)
		if jErr != nil {
			pkg.PrintError(jErr.Error())
		}

		jErr = ioutil.WriteFile(stampPath, stampData, os.FileMode(0660))
		if jErr != nil {
			pkg.PrintError(jErr.Error())
		}

		pkg.PrintTask("Done")

		return err
	},
}

func init() {
	rootCmd.AddCommand(fetchDepsCmd)
	fetchDepsCmd.Flags().BoolP("full-cef", "f", false, "Download the full CEF distribution (not actually implemented, yet)")
	fetchDepsCmd.Flags().BoolP("update", "u", false, "Update checksums")
}

func getProgressBar(length int64, desc string) *progressbar.ProgressBar {
	if os.Getenv("CI") == "true" {
		return progressbar.NewOptions64(length, progressbar.OptionSetVisibility(false))
		/*
			Sadly this still leaves a bunch of newlines on GH's log.

			return progressbar.NewOptions64(length, progressbar.OptionSetDescription(desc),
				progressbar.OptionSetWriter(os.Stderr), progressbar.OptionShowBytes(true),
				progressbar.OptionShowCount(), progressbar.OptionOnCompletion(func() {
					fmt.Fprint(os.Stderr, "\n")
				}),
				// Only show the result once at the end
				progressbar.OptionThrottle(1*time.Hour),
			)
		*/
	}

	return progressbar.DefaultBytes(length, desc)
}

func getConfig(projectRoot string) (depConfig, string, map[string]string, error) {
	var cfg depConfig
	cfgPath := filepath.Join(projectRoot, "packages", "build-tools", "DEPS.yml")
	cfgData, err := ioutil.ReadFile(cfgPath)
	if err != nil {
		return cfg, "", nil, eris.Wrapf(err, "Could not open file %s.", cfgPath)
	}

	err = yaml.Unmarshal(cfgData, &cfg)
	if err != nil {
		return cfg, "", nil, eris.Wrapf(err, "Failed to parse %s.", cfgPath)
	}

	stamps := map[string]string{}
	stampPath := filepath.Join(projectRoot, "packages", "build-tools", "DEPS.stamps")
	stampData, err := ioutil.ReadFile(stampPath)
	if err != nil {
		if !eris.Is(err, os.ErrNotExist) {
			return cfg, "", nil, eris.Wrapf(err, "Failed to read stamps file %s.", stampPath)
		}
	} else {
		err = json.Unmarshal(stampData, &stamps)
		if err != nil {
			return cfg, "", nil, eris.Wrapf(err, "Failed to parse JSON file %s.", stampPath)
		}
	}

	return cfg, string(cfgData), stamps, nil
}

func evalConditions(meta *depSpec, vars map[string]string) bool {
	varMatcher := regexp.MustCompile(`\{([A-Z0-9_]+)\}`)

	meta.URL = varMatcher.ReplaceAllStringFunc(meta.URL, func(varName string) string {
		value, ok := vars[varName[1:len(varName)-1]]
		if ok {
			return value
		} else {
			return ""
		}
	})

	for _, condition := range strings.Split(meta.Condition, ",") {
		if condition == "" {
			continue
		}

		value, ok := vars[strings.TrimSpace(condition)]
		if !ok || value == "" {
			return false
		}
	}

	for _, condition := range strings.Split(meta.Rejections, ",") {
		if condition == "" {
			continue
		}

		value, ok := vars[strings.TrimSpace(condition)]
		if ok && value != "" {
			return false
		}
	}
	return true
}

type yamlChange struct {
	Start       int
	End         int
	Replacement string
}

func downloadAndExtract(cmd *cobra.Command, cfg depConfig, cfgData string, stamps map[string]string, projectRoot string) error {
	client := &http.Client{
		Timeout: time.Minute * 30,
	}
	buf := make([]byte, 4096)

	fullCef, err := cmd.Flags().GetBool("full-cef")
	if err != nil {
		return err
	}
	fullStr := ""
	if fullCef {
		fullStr = "yes"
	}

	update, err := cmd.Flags().GetBool("update")
	if err != nil {
		return err
	}

	vars := cfg.Vars
	vars["full-cef"] = fullStr
	vars[runtime.GOARCH] = "true"
	vars[runtime.GOOS] = "true"
	if os.Getenv("CI") == "true" {
		vars["ci"] = "true"
	}

	changes := map[string]string{}
	cfgLines := strings.Split(cfgData, "\n")
	lineLength := make([]int, len(cfgLines))
	for idx, line := range cfgLines {
		lineLength[idx] = len(line) + 1
	}

	for name, meta := range cfg.Deps {
		// We eval the conditions even if we're updating because we have to evaluate the variable placeholders.
		skip := !evalConditions(&meta, vars)
		if skip {
			if !update {
				continue
			}
		}

		destPath := filepath.Join(projectRoot, meta.Dest)
		destInfo, err := os.Stat(destPath)
		destExists := err == nil

		stampToken := meta.URL + "#" + meta.Sha256
		stamp, ok := stamps[name]
		if ok && stampToken == stamp && destExists {
			continue
		}

		pkg.PrintSubtask(name + ":  " + meta.URL)
		if meta.Sha256 == "" && !update {
			return eris.Errorf("Dependency %s doesn't have a checksum", name)
		}

		arHandle, err := os.Create("deps_dl.tmp")
		if err != nil {
			return eris.Wrap(err, "Failed to create deps_dl.tmp")
		}
		defer func() {
			arHandle.Close()
			os.Remove("deps_dl.tmp")
		}()

		resp, err := client.Get(meta.URL)
		if err != nil {
			return eris.Wrapf(err, "Failed to start download for %s", meta.URL)
		}
		defer resp.Body.Close()

		hash := sha256.New()
		bar := getProgressBar(resp.ContentLength, "     download")
		for {
			n, err := resp.Body.Read(buf)
			if err != nil && n < 1 {
				if err == io.EOF {
					break
				}
				return eris.Wrapf(err, "Failed during download of %s", meta.URL)
			}

			_, err = hash.Write(buf[:n])
			if err != nil {
				return eris.Wrapf(err, "Failed to calculate checksum for %s", meta.URL)
			}

			_, err = arHandle.Write(buf[:n])
			if err != nil {
				return eris.Wrap(err, "Failed to write download to file deps_dl.tmp")
			}

			bar.Write(buf[:n])
		}
		bar.Finish()
		resp.Body.Close()

		digest := hex.EncodeToString(hash.Sum(nil))
		if digest != meta.Sha256 {
			if update {
				fmt.Println("      Updating checksum")
				changes[name] = digest
			} else {
				return eris.New("Checksum check failed")
			}
		}

		if skip {
			continue
		}

		if destExists {
			pkg.PrintSubtask(fmt.Sprintf("Remove %s", destPath))
			if destInfo.IsDir() {
				err = os.RemoveAll(destPath)
			} else {
				err = os.Remove(destPath)
			}
			if err != nil {
				return err
			}
		}

		extractor, err := getExtractor(meta.URL)
		if err != nil {
			return err
		}

		arHandle.Seek(0, io.SeekStart)
		bar = getProgressBar(resp.ContentLength, "      extract")
		err = extractor(arHandle, bar, projectRoot, name, meta)
		if err != nil {
			return err
		}

		if runtime.GOOS != "windows" {
			// .zip files don't carry permissions which means we have to manually fix permissions for binaries in .zip files
			for _, binPath := range meta.MarkExec {
				binPath = filepath.Join(projectRoot, meta.Dest, binPath)
				fi, err := os.Stat(binPath)
				if err != nil {
					return eris.Wrapf(err, "Failed to read permissions for %s", binPath)
				}

				err = os.Chmod(binPath, fi.Mode()|0700)
				if err != nil {
					return eris.Wrapf(err, "Failed to mark %s as executable", binPath)
				}
			}
		}

		stamps[name] = stampToken
	}

	if update {
		pkg.PrintTask("Updating DEPS.yml")
		generated := cfgData
		for name, newChecksum := range changes {
			pos := strings.Index(generated, name+":\n")
			if pos == -1 {
				return eris.Errorf("Failed to find the section for %s!", name)
			}

			subPos := strings.Index(generated[pos:], "sha256: "+cfg.Deps[name].Sha256)
			if subPos == -1 {
				if cfg.Deps[name].Sha256 == "" {
					endPos := strings.Index(generated[pos:], "\n\n")
					if endPos < subPos {
						fmt.Printf("     Couldn't find checksum section for %s.\n", name)
					} else {
						start := pos + len(name) + 2
						generated = generated[:start] + "    sha256: " + newChecksum + "\n" + generated[start:]
					}
				} else {
					fmt.Printf("     Couldn't find checksum section for %s.\n", name)
				}
			} else {
				start := pos + subPos + 8
				end := start + len(cfg.Deps[name].Sha256)
				generated = generated[:start] + newChecksum + generated[end:]
			}
		}

		ioutil.WriteFile(filepath.Join(projectRoot, "packages", "build-tools", "DEPS.yml"), []byte(generated), os.FileMode(0660))
	}

	return nil
}

type (
	archiveExtractor func(*os.File, *progressbar.ProgressBar, string, string, depSpec) error
	archiveDetector  func(string) (archiveExtractor, bool)
)

func openExtractorDest(destPath string, item string, ds depSpec) (*os.File, string, error) {
	// normalize the path and strip ds.strip elements from the beginning
	pathParts := strings.Split(filepath.Clean(item), string(filepath.Separator))
	dest := filepath.Join(destPath, strings.Join(pathParts[ds.Strip:], string(filepath.Separator)))

	if dest == destPath {
		return nil, "/", nil
	}

	destParent := filepath.Dir(dest)
	err := os.MkdirAll(destParent, os.FileMode(0770))
	if err != nil {
		return nil, "", eris.Wrapf(err, "Failed to create directory %s", destParent)
	}

	destHandle, err := os.Create(dest)
	if err != nil {
		return nil, "", eris.Wrapf(err, "Failed to create file %s", dest)
	}

	return destHandle, dest, nil
}

func getExtractor(url string) (archiveExtractor, error) {
	if strings.HasSuffix(url, ".zip") {
		return func(f *os.File, bar *progressbar.ProgressBar, projectRoot string, name string, ds depSpec) error {
			stat, err := f.Stat()
			if err != nil {
				return err
			}

			archive, err := zip.NewReader(f, stat.Size())
			if err != nil {
				return err
			}

			buf := make([]byte, 4096)
			destPath := filepath.Join(projectRoot, ds.Dest)
			for _, item := range archive.File {
				if strings.HasSuffix(item.Name, "/") {
					continue
				}
				destHandle, dest, err := openExtractorDest(destPath, item.Name, ds)
				if err != nil {
					return err
				}

				if destHandle == nil {
					continue
				}
				defer destHandle.Close()

				itemHandle, err := item.Open()
				if err != nil {
					return eris.Wrap(err, "Failed to open archive entry")
				}
				defer itemHandle.Close()

				for {
					n, err := itemHandle.Read(buf)
					if err != nil && n < 1 {
						if err == io.EOF {
							break
						}
						return eris.Wrapf(err, "Failed to read archive entry %s", item.Name)
					}

					_, err = destHandle.Write(buf[:n])
					if err != nil {
						return eris.Wrapf(err, "Failed to write extracted file %s", dest)
					}

					pos, err := f.Seek(0, io.SeekCurrent)
					if err == nil {
						bar.Set64(pos)
					}
				}

				itemHandle.Close()
				destHandle.Close()
			}

			return nil
		}, nil
	}

	if strings.HasSuffix(url, ".tar.gz") {
		return func(f *os.File, bar *progressbar.ProgressBar, projectRoot string, name string, ds depSpec) error {
			reader, err := gzip.NewReader(f)
			if err != nil {
				return err
			}
			defer reader.Close()

			return extractTar(reader, f, bar, projectRoot, name, ds)
		}, nil
	}

	if strings.HasSuffix(url, ".tar.bz2") {
		return func(f *os.File, bar *progressbar.ProgressBar, projectRoot string, name string, ds depSpec) error {
			reader := bzip2.NewReader(f)

			return extractTar(reader, f, bar, projectRoot, name, ds)
		}, nil
	}

	if strings.HasSuffix(url, ".tar.xz") {
		return func(f *os.File, bar *progressbar.ProgressBar, projectRoot, name string, ds depSpec) error {
			reader, err := xz.NewReader(f)
			if err != nil {
				return err
			}

			return extractTar(reader, f, bar, projectRoot, name, ds)
		}, nil
	}

	return nil, eris.New("Archive format not supported")
}

func extractTar(r io.Reader, f *os.File, bar *progressbar.ProgressBar, projectRoot string, name string, ds depSpec) error {
	buf := make([]byte, 4096)
	archive := tar.NewReader(r)
	destPath := filepath.Join(projectRoot, ds.Dest)

	for {
		item, err := archive.Next()
		if err != nil {
			if err == io.EOF {
				break
			}

			return eris.Wrap(err, "Failed to read archive entry")
		}

		fi := item.FileInfo()
		if fi.IsDir() {
			continue
		}

		destHandle, dest, err := openExtractorDest(destPath, item.Name, ds)
		if err != nil {
			return err
		}
		defer destHandle.Close()

		if item.Typeflag&tar.TypeSymlink == tar.TypeSymlink {
			destHandle.Close()
			err := os.Remove(dest)
			if err != nil {
				return eris.Wrapf(err, "Failed to remove placeholder file %s", dest)
			}

			err = os.Symlink(item.Linkname, dest)
			if err != nil {
				return eris.Wrapf(err, "Failed to create symlink %s pointing to %s", dest, item.Linkname)
			}
			continue
		}

		os.Chmod(dest, fi.Mode())

		for {
			n, err := archive.Read(buf)
			if err != nil && n < 1 {
				if err == io.EOF {
					break
				}
				return eris.Wrapf(err, "Failed to read archive entry %s", item.Name)
			}

			_, err = destHandle.Write(buf[:n])
			if err != nil {
				return eris.Wrapf(err, "Failed to write extracted file %s", dest)
			}

			pos, err := f.Seek(0, io.SeekCurrent)
			if err == nil {
				bar.Set64(pos)
			}
		}

		destHandle.Close()
	}

	return nil
}
