// Package main implements a simple CLI for the buildsys package
package cmd

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/ngld/knossos/packages/build-tools/pkg/buildsys"
	"github.com/rotisserie/eris"
	"github.com/rs/zerolog"
	"github.com/spf13/cobra"
)

var RootCmd = &cobra.Command{
	Use:   "task",
	Short: "Simple build system for Knossos",
	Long:  `This command parses the first tasks.star file it finds and executes the given tasks.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		taskArgs := make([]string, 0)
		options := make(map[string]string)
		dryRun, err := cmd.Flags().GetBool("dry")
		if err != nil {
			return err
		}

		force, err := cmd.Flags().GetBool("force")
		if err != nil {
			return err
		}

		for _, part := range args {
			pos := strings.Index(part, "=")
			if pos > -1 {
				options[part[:pos]] = part[pos+1:]
			} else {
				taskArgs = append(taskArgs, part)
			}
		}

		logger := zerolog.New(NewConsoleWriter())
		ctx := context.Background()
		ctx = buildsys.WithLogger(ctx, &logger)

		// search the next tasks.star file
		wd, err := os.Getwd()
		if err != nil {
			logger.Fatal().Err(err).Msg("Failed to retrieve the current working directory")
		}

		path := wd
		var taskPath string
		for {
			taskPath = filepath.Join(path, "tasks.star")
			_, err := os.Stat(taskPath)
			if err == nil {
				break
			}
			if !eris.Is(err, os.ErrNotExist) {
				logger.Fatal().Err(err).Msgf("Failed to check %s", taskPath)
			}

			parent := filepath.Dir(path)
			if parent == path {
				logger.Fatal().Msg("No tasks.star file found")
			}

			path = parent
		}

		taskPath, err = filepath.Rel(wd, taskPath)
		if err != nil {
			logger.Fatal().Err(err).Msg("Failed to simplify path")
		}

		taskList, err := buildsys.Parse(ctx, taskPath, filepath.Dir(taskPath), options)
		if err != nil {
			logger.Fatal().Err(err).Msg("Failed to parse tasks")
		}

		for _, name := range taskArgs {
			task, ok := taskList[name]
			if !ok {
				logger.Fatal().Msgf("Task %s not found", name)
			}

			err = buildsys.RunTask(ctx, task, taskList, dryRun, force, false)
			if err != nil {
				logger.Fatal().Err(err).Msgf("Failed task %s:", name)
			}
		}

		if len(taskArgs) == 0 {
			fmt.Println("Available tasks:")
			maxNameLen := 0
			sortedNames := make([]string, 0)
			for _, task := range taskList {
				nameLen := len(task.Short)
				if nameLen > maxNameLen {
					maxNameLen = nameLen
				}

				sortedNames = append(sortedNames, task.Short)
			}

			sort.Strings(sortedNames)

			lineFmt := fmt.Sprintf(" * %%-%ds %%s\n", maxNameLen+3)
			for _, name := range sortedNames {
				fmt.Printf(lineFmt, name+":", taskList[name].Desc)
			}
		}

		return nil
	},
}

func init() {
	RootCmd.Flags().BoolP("dry", "n", false, "dry run; only print the commands, don't execute anything")
	RootCmd.Flags().BoolP("force", "f", false, "force build; always execute the passed steps even if they don't have to run")
}
