package cmd

import (
	"github.com/spf13/cobra"

	"github.com/ngld/knossos/packages/build-tools/pkg/buildsys/cmd"
)

var rootCmd = &cobra.Command{
	Use:   "tool",
	Short: "Build tools for Knossos",
	Long: `This command bundles several tools that are used to build Knossos.
This includes tools to download & extract dependencies, to install Go dependencies, ...`,
}

func init() {
	rootCmd.AddCommand(cmd.RootCmd)
}

func Execute() {
	cobra.CheckErr(rootCmd.Execute())
}
