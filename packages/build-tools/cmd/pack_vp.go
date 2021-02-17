package cmd

import (
	"os"
	"path/filepath"

	"github.com/rotisserie/eris"
	"github.com/spf13/cobra"

	"github.com/ngld/knossos/packages/libknossos/pkg/archives"
)

var packVpCmd = &cobra.Command{
	Use:   "pack-vp archive_name content_directory",
	Short: "Recursively packs the content of the passed directory into a .vp archive",
	Long: `Pass the name of the .vp file that should be generated and a directory with
the intended contents.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) != 2 {
			return eris.New("Expected 2 arguments!")
		}

		writer, err := archives.NewVpWriter(args[0])
		if err != nil {
			return err
		}

		err = walkDirectory(writer, args[1])
		if err != nil {
			return err
		}

		err = writer.Close()
		if err != nil {
			return err
		}
		return nil
	},
}

func init() {
	rootCmd.AddCommand(packVpCmd)
}

func walkDirectory(writer *archives.VpWriter, dir string) error {
	f, err := os.Open(dir)
	if err != nil {
		return eris.Wrapf(err, "Failed to open dir %s", dir)
	}

	infos, err := f.Readdir(0)
	if err != nil {
		f.Close()
		return eris.Wrapf(err, "Failed to read dir %s", dir)
	}
	f.Close()

	for _, info := range infos {
		itemPath := filepath.Join(dir, info.Name())
		if info.IsDir() {
			writer.OpenDirectory(info.Name())
			err = walkDirectory(writer, itemPath)
			if err != nil {
				return err
			}
			writer.CloseDirectory()
		} else {
			f, err = os.Open(itemPath)
			if err != nil {
				return eris.Wrapf(err, "Failed to open file %s", itemPath)
			}

			err = writer.WriteFile(info.Name(), f)
			if err != nil {
				f.Close()
				return eris.Wrapf(err, "Failed to pack file %s", itemPath)
			}
			f.Close()
		}
	}

	return nil
}
