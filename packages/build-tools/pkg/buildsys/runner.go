package buildsys

import (
	"context"
	"fmt"
	"io"
	"os"
	"strings"
	"time"

	"github.com/rotisserie/eris"
	"mvdan.cc/sh/v3/expand"
	"mvdan.cc/sh/v3/interp"
	"mvdan.cc/sh/v3/syntax"
)

type runTasksCacheKey struct{}

func getTaskEnv(task *Task) expand.Environ {
	envVars := os.Environ()

	for name, value := range task.Env {
		envVars = append(envVars, fmt.Sprintf("%s=%s", name, value))
	}

	return expand.ListEnviron(envVars...)
}

var defaultExecHandler = interp.DefaultExecHandler(2)

func execHandler(ctx context.Context, args []string) error {
	if len(args) > 0 {
		switch args[0] {
		case "mv":
		case "rm":
		case "mkdir":
			// always use our cross-platform implementation for these operations to make sure
			// they behave consistently
			args = append([]string{"tool"}, args...)
		}
	}

	return defaultExecHandler(ctx, args)
}

var defaultOpenHandler = interp.DefaultOpenHandler()

func openHandler(ctx context.Context, path string, flag int, perm os.FileMode) (io.ReadWriteCloser, error) {
	if path == "/dev/null" {
		path = os.DevNull
	}

	return defaultOpenHandler(ctx, path, flag, perm)
}

// RunTask executes the given task
func RunTask(ctx context.Context, task *Task, tasks TaskList, dryRun, canSkip bool) error {
	if ctx.Err() != nil {
		return ctx.Err()
	}

	runTasks, ok := ctx.Value(runTasksCacheKey{}).(map[string]bool)
	if !ok {
		runTasks = map[string]bool{}
		ctx = context.WithValue(ctx, runTasksCacheKey{}, runTasks)
	}

	status, ok := runTasks[task.Short]
	if ok {
		if status {
			// this task has already been run
			return nil
		}

		if !status {
			return eris.Errorf("Task %s was called recursively", task.Short)
		}
	}

	runTasks[task.Short] = false

	for _, dep := range task.Deps {
		if !runTasks[dep] {
			depTask, ok := tasks[dep]
			if !ok {
				return eris.Errorf("Task %s not found", dep)
			}

			err := RunTask(ctx, depTask, tasks, dryRun, true)
			if err != nil {
				return eris.Wrapf(err, "Task %s failed due to its dependency %s", task.Short, dep)
			}
		}
	}

	if canSkip {
		for _, item := range task.SkipIfExists {
			_, err := os.Stat(item)
			if err == nil {
				log(ctx).Info().
					Str("task", task.Short).
					Str("status", "skipped").
					Str("path", item).
					Msgf("Skipped because %s exists", item)

				runTasks[task.Short] = true
				return nil
			}
			if !eris.Is(err, os.ErrNotExist) {
				return eris.Wrapf(err, "Failed to check %s", item)
			}
		}
	}

	var newestInput time.Time
	for _, item := range task.Inputs {
		info, err := os.Stat(item)
		if err != nil {
			return eris.Wrapf(err, "Failed to check input %s", item)
		}

		if info.ModTime().Sub(newestInput) > 0 {
			newestInput = info.ModTime()
		}
	}

	if !newestInput.IsZero() {
		var newestOutput time.Time
		oldestOutput := time.Now()

		for _, item := range task.Outputs {
			info, err := os.Stat(item)
			if err != nil && !eris.Is(err, os.ErrNotExist) {
				return eris.Wrapf(err, "Failed to check output %s", item)
			}

			if err == nil {
				mt := info.ModTime()
				if mt.Sub(newestOutput) > 0 {
					newestOutput = mt
				}

				if oldestOutput.Sub(mt) > 0 {
					oldestOutput = mt
				}
			}
		}

		if newestOutput.Sub(oldestOutput) > 10*time.Minute {
			log(ctx).Warn().
				Str("task", task.Short).
				Msgf("Oldest output is %f minutes older than the newest output", newestOutput.Sub(oldestOutput).Minutes())
		}

		if newestOutput.Sub(newestInput) > 0 {
			log(ctx).Info().
				Str("task", task.Short).
				Str("status", "uptodate").
				Msgf("Nothing to do (output is %f seconds newer)", newestOutput.Sub(newestInput).Seconds())

			runTasks[task.Short] = true
			return nil
		}
	}

	// With the skip and input/output checks done, we can finally start executing
	runner, err := interp.New(
		interp.Dir(task.Base),
		interp.Env(getTaskEnv(task)),
		interp.ExecHandler(execHandler),
		interp.OpenHandler(openHandler),
		interp.StdIO(nil, os.Stdout, os.Stderr),
		interp.Params("-e"),
	)
	if err != nil {
		return eris.Wrap(err, "Failed to initialize runner")
	}

	printer := syntax.NewPrinter(
		syntax.Minify(true),
	)
	strBuffer := strings.Builder{}

	for _, item := range task.Cmds {
		switch value := item.(type) {
		case *syntax.Stmt:
			strBuffer.Reset()
			printer.Print(&strBuffer, value)
			log(ctx).Info().
				Str("task", task.Short).
				Str("status", "executing").
				Bool("command", true).
				Msg(strBuffer.String())

			if !dryRun {
				err = runner.Run(ctx, value)
				if err != nil {
					return err
				}

				if runner.Exited() {
					return nil
				}
			}
		case *Task:
			err = RunTask(ctx, value, tasks, dryRun, true)
			if err != nil {
				return err
			}
		default:
			return eris.Errorf("Found unkown task item %v", item)
		}

		if err = ctx.Err(); err != nil {
			return err
		}
	}

	if task.Short != "" {
		runTasks[task.Short] = true
	}
	return nil
}
