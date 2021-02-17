package cmd

import (
	"github.com/ngld/knossos/packages/build-tools/pkg"
	"github.com/spf13/cobra"
)

var installToolsCmd = &cobra.Command{
	Use:   "install-tools",
	Short: "Installs Go CLI tools",
	Long: `Installs the tools listed in packages/build-tools/tools.go into the
workspace .tools directory. If you have direnv enabled, they will be available
in your PATH.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		return pkg.InstallTools()
	},
}

func init() {
	rootCmd.AddCommand(installToolsCmd)
}
