package buildsys

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/rotisserie/eris"
	"mvdan.cc/sh/v3/expand"
	"mvdan.cc/sh/v3/interp"
	"mvdan.cc/sh/v3/syntax"
)

type (
	runtimeCtxKey struct{}
	runtimeCtx    struct {
		runTasks    map[string]bool
		projectRoot string
	}
)

func getRuntimeCtx(ctx context.Context) *runtimeCtx {
	return ctx.Value(runtimeCtxKey{}).(*runtimeCtx)
}

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
			fallthrough
		case "rm":
			fallthrough
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

func resolvePatternLists(ctx context.Context, base string, patterns []string) ([]string, error) {
	result := []string{}
	cfg := expand.Config{
		ReadDir:  shellReadDir,
		GlobStar: true,
	}

	parser := syntax.NewParser()
	parserCtx := &parserCtx{
		filepath:    "invalid",
		projectRoot: getRuntimeCtx(ctx).projectRoot,
	}

	for _, item := range patterns {
		item = normalizePath(parserCtx, base, item)
		item = filepath.ToSlash(item)

		words := make([]*syntax.Word, 0)
		parser.Words(strings.NewReader(item), func(w *syntax.Word) bool {
			words = append(words, w)
			return true
		})

		matches, err := expand.Fields(&cfg, words...)
		if err != nil {
			return nil, eris.Wrapf(err, "Failed to resolve pattern %s", item)
		}

		for _, match := range matches {
			// If a pattern didn't match anything, it's returned as a result. Skip those results.
			if !strings.Contains(match, "*") {
				result = append(result, match)
			}
		}
	}
	return result, nil
}

// RunTask executes the given task
func RunTask(ctx context.Context, projectRoot, task string, tasks TaskList, dryRun, force bool) error {
	rctx := runtimeCtx{
		projectRoot: projectRoot,
		runTasks:    make(map[string]bool),
	}

	ctx = context.WithValue(ctx, runtimeCtxKey{}, &rctx)
	taskMeta, found := tasks[task]
	if !found {
		return eris.Errorf("Task %s not found", task)
	}

	return runTaskInternal(ctx, taskMeta, tasks, dryRun, force, true)
}

func runTaskInternal(ctx context.Context, task *Task, tasks TaskList, dryRun, force, canSkip bool) error {
	if ctx.Err() != nil {
		return ctx.Err()
	}

	rctx := getRuntimeCtx(ctx)
	status, ok := rctx.runTasks[task.Short]
	if ok {
		if status {
			// this task has already been run
			log(ctx).Debug().Msgf("Task %s already run", task.Short)
			return nil
		}

		if !status {
			return eris.Errorf("Task %s was called recursively", task.Short)
		}
	}

	rctx.runTasks[task.Short] = false

	for _, dep := range task.Deps {
		if !rctx.runTasks[dep] {
			depTask, ok := tasks[dep]
			if !ok {
				return eris.Errorf("Task %s not found", dep)
			}

			err := runTaskInternal(ctx, depTask, tasks, dryRun, false, true)
			if err != nil {
				return eris.Wrapf(err, "Task %s failed due to its dependency %s", task.Short, dep)
			}
		}
	}

	if canSkip && !force {
		skipList, err := resolvePatternLists(ctx, task.Base, task.SkipIfExists)
		if err != nil {
			return eris.Wrapf(err, "failed to resolve skipIfExists list")
		}

		found := 0
		for _, item := range skipList {
			_, err := os.Stat(item)
			if err == nil {
				found++
			} else if !eris.Is(err, os.ErrNotExist) {
				return eris.Wrapf(err, "Failed to check %s", item)
			}
		}

		if found > 0 && found == len(skipList) {
			log(ctx).Info().
				Str("task", task.Short).
				Msg("skipped because all skip files exist")

			rctx.runTasks[task.Short] = true
			return nil
		}
	}

	if !force {
		var newestInput time.Time
		inputList, err := resolvePatternLists(ctx, task.Base, task.Inputs)
		if err != nil {
			return eris.Wrap(err, "failed to resolve inputs")
		}

		outputList, err := resolvePatternLists(ctx, task.Base, task.Outputs)
		if err != nil {
			return eris.Wrap(err, "failed to resolve output list")
		}

		for _, item := range inputList {
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

			for _, item := range outputList {
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
					Msgf("oldest output is %f minutes older than the newest output", newestOutput.Sub(oldestOutput).Minutes())
			}

			if newestOutput.Sub(newestInput) > 0 {
				log(ctx).Info().
					Str("task", task.Short).
					Msgf("nothing to do (output is %f seconds newer)", newestOutput.Sub(newestInput).Seconds())

				rctx.runTasks[task.Short] = true
				return nil
			}
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

	parser := syntax.NewParser()
	printer := syntax.NewPrinter(
		syntax.Minify(true),
	)
	strBuffer := strings.Builder{}

	for _, item := range task.Cmds {
		stmts, err := item.ToShellStmts(parser)
		if err != nil {
			return eris.Wrap(err, "failed to parser shell script")
		}
		if stmts != nil {
			for _, stm := range stmts {
				strBuffer.Reset()
				printer.Print(&strBuffer, stm)
				log(ctx).Info().
					Str("task", task.Short).
					Bool("command", true).
					Msg(strBuffer.String())

				if !dryRun {
					err = runner.Run(ctx, stm)
					if err != nil {
						return err
					}

					if runner.Exited() {
						return nil
					}
				}
			}
		} else {
			subTask, err := item.ToTask()
			if err != nil {
				return eris.Wrap(err, "failed to retrieve task ref")
			}

			if subTask != nil {
				err = runTaskInternal(ctx, subTask, tasks, dryRun, force, true)
				if err != nil {
					return err
				}
			} else {
				return eris.Errorf("unexpected task command %+v", item)
			}
		}

		if err = ctx.Err(); err != nil {
			return err
		}
	}

	if task.Short != "" {
		rctx.runTasks[task.Short] = true
	}
	return nil
}
