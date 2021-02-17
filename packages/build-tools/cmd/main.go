package cmd

import "github.com/spf13/cobra"

var rootCmd = &cobra.Command{
	Use:   "tool",
	Short: "Build tools for Knossos",
	Long: `This command bundles several tools that are used to build Knossos.
This includes tools to download & extract dependencies, to install Go dependencies, ...`,
}

func init() {
	// TODO
}

func Execute() {
	cobra.CheckErr(rootCmd.Execute())
}
