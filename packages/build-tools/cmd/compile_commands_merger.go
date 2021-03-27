package cmd

import (
	"encoding/json"
	"io/ioutil"

	"github.com/rotisserie/eris"
	"github.com/spf13/cobra"
)

var mergeCompileCommansCmd = &cobra.Command{
	Use:   "merge-compile-commands <output file> <input files...>",
	Short: "Merges several compile_commands.json files. Assumes that only absolute paths are used.",
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) < 2 {
			return eris.Errorf("Expected at least 2 arguments but got %d!", len(args))
		}

		output := make([]interface{}, 0)
		var chunk []interface{}
		for _, fpath := range args[1:] {
			data, err := ioutil.ReadFile(fpath)
			if err != nil {
				return eris.Wrapf(err, "failed to read %s", fpath)
			}

			err = json.Unmarshal(data, &chunk)
			if err != nil {
				return eris.Wrapf(err, "failed to decode %s", fpath)
			}

			output = append(output, chunk...)
		}

		data, err := json.MarshalIndent(output, "", "  ")
		if err != nil {
			return eris.Wrap(err, "failed to encode output")
		}

		err = ioutil.WriteFile(args[0], data, 0660)
		if err != nil {
			return eris.Wrapf(err, "failed to write to %s", args[0])
		}

		return nil
	},
}

func init() {
	rootCmd.AddCommand(mergeCompileCommansCmd)
}
