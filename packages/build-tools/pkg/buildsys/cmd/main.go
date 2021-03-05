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
	Use:   "task [-l|-o] | [-nf] task1 task2 ...",
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

		listTasks, err := cmd.Flags().GetBool("list")
		if err != nil {
			return err
		}

		listOpts, err := cmd.Flags().GetBool("options")
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

		// sanity checks
		if len(options) > 0 && (len(taskArgs) != 1 || taskArgs[0] != "configure") {
			logger.Fatal().Msg("Options can only be passed to the configure task")
		}

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

		isConfigure := len(taskArgs) > 0 && taskArgs[0] == "configure"
		cacheFile := taskPath + ".cache"
		projectRoot := filepath.Dir(taskPath)
		var taskList buildsys.TaskList
		rebuildCache := isConfigure

		if !rebuildCache {
			cacheInfo, err := os.Stat(cacheFile)
			if err != nil {
				if !eris.Is(err, os.ErrNotExist) {
					logger.Fatal().Err(err).Msg("Failed to check cache")
				}
			} else {
				scriptInfo, err := os.Stat(taskPath)
				if err != nil {
					logger.Fatal().Err(err).Msg("Failed to check task file")
				}

				if cacheInfo.ModTime().Sub(scriptInfo.ModTime()) < 0 {
					// script is newer than our cache
					rebuildCache = true
				}
			}
		}

		if !isConfigure {
			// We read the cache even if rebuildCache is true because we need the options from the last configure run.
			// Overwriting options here is fine because the sanity check earlier ensures that options are only passed
			// on the CLI for the configure task.
			options, taskList, err = buildsys.ReadCache(cacheFile)
			if err != nil && !eris.Is(err, os.ErrNotExist) {
				logger.Fatal().Err(err).Msg("Failed to open cache")
			}
		}

		if rebuildCache || listOpts {
			var scriptOptions map[string]buildsys.ScriptOption
			taskList, scriptOptions, err = buildsys.RunScript(ctx, taskPath, filepath.Dir(taskPath), options, !listOpts)
			if err != nil {
				logger.Fatal().Err(err).Msg("Failed to parse tasks")
			}

			if listOpts {
				return printOptHelp(scriptOptions)
			}

			err = buildsys.WriteCache(cacheFile, options, taskList)
			if err != nil {
				logger.Fatal().Err(err).Msg("Failed to cache processed tasks")
			}

			if isConfigure {
				logger.Info().Msg("Done")
				return nil
			}
		}

		if taskList == nil {
			logger.Fatal().Msg(
				`Please run "task configure" before you run any other task. For a list of available options, check` +
					` "task configure -o"`,
			)
		}

		if !listTasks {
			for _, name := range taskArgs {
				err = buildsys.RunTask(ctx, projectRoot, name, taskList, dryRun, force)
				if err != nil {
					logger.Fatal().Err(err).Msgf("Failed task %s:", name)
				}
			}
		}

		if len(taskArgs) == 0 || listTasks {
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

func printOptHelp(options map[string]buildsys.ScriptOption) error {
	table := make([][2]string, 0)
	maxCol := 0
	termCols := 80

	for name, option := range options {
		name = fmt.Sprintf("%s=%s", name, option.Default())

		if len(name) > maxCol {
			maxCol = len(name)
		}

		table = append(table, [2]string{name, option.Help})
	}

	lineFmt := fmt.Sprintf("%%-%ds %%s\n", maxCol+3)
	for _, items := range table {
		if len(items[1]) > termCols {
			fmt.Printf(lineFmt, items[0], items[1][:termCols])

			pos := termCols
			for pos < len(items[1]) {
				end := pos + termCols
				if end > len(items[1]) {
					end = len(items[1])
				}

				fmt.Printf(lineFmt, "", items[1][pos:end])
				pos = end
			}
		} else {
			fmt.Printf(lineFmt, items[0], items[1])
		}
	}

	return nil
}

func init() {
	f := RootCmd.Flags()
	f.BoolP("dry", "n", false, "dry run; only print the commands, don't execute anything")
	f.BoolP("force", "f", false, "force build; always execute the passed steps even if they don't have to run")
	f.BoolP("list", "l", false, "list available tasks")
	f.BoolP("options", "o", false, "list configure options")
}
