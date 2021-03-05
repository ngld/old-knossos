package cmd

import (
	"os"
	"path/filepath"
	"runtime"

	"github.com/rotisserie/eris"
	"github.com/spf13/cobra"
)

var mvCmd = &cobra.Command{
	Use:   "mv",
	Short: "Cross-platform implementation of the POSIX mv command",
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) < 2 {
			return eris.New("Not enough parameters")
		}

		dest := filepath.Clean(args[len(args)-1])
		destParent := filepath.Dir(dest)
		info, err := os.Stat(destParent)
		if err != nil {
			return eris.Wrapf(err, "Could not find destination directory %s", destParent)
		}

		if !info.IsDir() {
			return eris.Errorf("%s is not a directory!", destParent)
		}

		info, err = os.Stat(dest)
		if err != nil && !eris.Is(err, os.ErrNotExist) {
			return eris.Wrapf(err, "Failed to retrieve info about destination %s", dest)
		}

		if len(args) > 2 && !info.IsDir() {
			return eris.Errorf("Can't move multiple items to %s because it is not a directory!", dest)
		}

		items := []string{}
		if runtime.GOOS == "windows" {
			for _, arg := range args[:len(args)-1] {
				matches, err := filepath.Glob(arg)
				if err != nil {
					return eris.Wrapf(err, "Failed to resolve parameter %s", arg)
				}

				if matches == nil {
					return eris.Errorf("Pattern %s produced no matches!", arg)
				}

				items = append(items, matches...)
			}
		} else {
			items = args[:len(args)-1]
		}

		for _, item := range items {
			itemDest := filepath.Join(dest, filepath.Base(item))
			err = os.Rename(item, itemDest)
			if err != nil {
				return eris.Wrapf(err, "Failed to move %s to %s", item, itemDest)
			}
		}

		return nil
	},
}

var rmCmd = &cobra.Command{
	Use:   "rm",
	Short: "A cross-platform implementation of the POSIX rm command",
	RunE: func(cmd *cobra.Command, args []string) error {
		items := []string{}
		recursive, err := cmd.Flags().GetBool("recursive")
		if err != nil {
			return err
		}

		force, err := cmd.Flags().GetBool("force")
		if err != nil {
			return err
		}

		if runtime.GOOS == "windows" {
			for _, arg := range args {
				matches, err := filepath.Glob(arg)
				if err != nil {
					return eris.Wrapf(err, "Failed to resolve pattern %s", arg)
				}

				if matches == nil {
					if force {
						continue
					} else {
						return eris.Errorf("Pattern %s produced no matches", arg)
					}
				}

				items = append(items, matches...)
			}
		} else {
			items = args
		}

		for _, item := range items {
			info, err := os.Stat(item)
			if err != nil {
				return eris.Wrapf(err, "Could not stat %s", item)
			}

			if info.IsDir() && !recursive {
				return eris.Errorf("%s is a directory but -r wasn't passed", item)
			}
		}

		for _, item := range items {
			err := os.RemoveAll(item)
			if err != nil && (!force || !eris.Is(err, os.ErrNotExist)) {
				return eris.Wrapf(err, "Could not delete %s", item)
			}
		}

		return nil
	},
}

var mkdirCmd = &cobra.Command{
	Use:   "mkdir",
	Short: "A cross-platform implementation of the POSIX mkdir command",
	RunE: func(cmd *cobra.Command, args []string) error {
		makeParents, err := cmd.Flags().GetBool("parents")
		if err != nil {
			return err
		}

		for _, item := range args {
			if makeParents {
				err = os.MkdirAll(item, 0770)
			} else {
				err = os.Mkdir(item, 0770)
			}

			if err != nil {
				return eris.Wrapf(err, "Failed to create %s", item)
			}
		}

		return nil
	},
}

func init() {
	rmCmd.Flags().BoolP("recursive", "r", false, "recursively delete directories")
	rmCmd.Flags().BoolP("force", "f", false, "suppresses errors caused by missing files/folders")
	mkdirCmd.Flags().BoolP("parents", "p", false, "create parent directories as needed")

	rootCmd.AddCommand(mvCmd)
	rootCmd.AddCommand(rmCmd)
	rootCmd.AddCommand(mkdirCmd)
}
