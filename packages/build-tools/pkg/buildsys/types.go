package buildsys

import (
	"fmt"
	"strings"

	"github.com/rotisserie/eris"
	"go.starlark.net/starlark"
	starsyntax "go.starlark.net/syntax"
	"mvdan.cc/sh/v3/syntax"
)

type TaskCmdScript struct {
	TaskName string
	Content  string
	Index    int
}

func (s TaskCmdScript) ToTask() (*Task, error) {
	return nil, nil
}

func (s TaskCmdScript) ToShellStmts(parser *syntax.Parser) ([]*syntax.Stmt, error) {
	reader := strings.NewReader(s.Content)
	result, err := parser.Parse(reader, fmt.Sprintf("%s:%d", s.TaskName, s.Index))
	if err != nil {
		return nil, eris.Wrapf(err, "failed to parse command %s", s.Content)
	}

	return result.Stmts, nil
}

type TaskCmdTaskRef struct {
	Task *Task
}

func (t TaskCmdTaskRef) ToTask() (*Task, error) {
	return t.Task, nil
}

func (t TaskCmdTaskRef) ToShellStmts(*syntax.Parser) ([]*syntax.Stmt, error) {
	return nil, nil
}

type TaskCmd interface {
	ToTask() (*Task, error)
	ToShellStmts(*syntax.Parser) ([]*syntax.Stmt, error)
}

// Task contains the processed values passed to task() by the task script
type Task struct {
	Env          map[string]string
	Short        string
	Desc         string
	Base         string
	Inputs       []string
	Deps         []string
	SkipIfExists []string
	Outputs      []string
	Cmds         []TaskCmd
	Hidden       bool
}

// TaskList maps short names to each relevant task
type TaskList map[string]*Task

type ScriptOption struct {
	DefaultValue starlark.String
	Help         string
}

func (o ScriptOption) Default() string {
	return o.DefaultValue.GoString()
}

// Implement starlark.Value for *Task

// String returns a string representation of the task
func (t *Task) String() string {
	return fmt.Sprintf("<Task %s: %s>", t.Short, t.Desc)
}

// Type always returns "task" to indicate this type
func (t *Task) Type() string {
	return "task"
}

// Freeze doesn't do anything since tasks are immutable anyway
func (t *Task) Freeze() {}

// Truth always returns true since a task can't be nil or None
func (t *Task) Truth() starlark.Bool {
	return starlark.True
}

// Hash always returns an error since task is not hashable
// It could be but I don't think implementing a hash over all contained values
// is worth it considering that the hash is only used by Starlake's dict type.
func (t *Task) Hash() (uint32, error) {
	return 0, eris.New("task is not a hashable type")
}

type StarlarkPath string

func (p StarlarkPath) String() string {
	return starlark.String(p).String()
}

func (p StarlarkPath) Type() string {
	return "path"
}

func (p StarlarkPath) Freeze() {}

func (p StarlarkPath) Truth() starlark.Bool {
	return p != ""
}

func (p StarlarkPath) Hash() (uint32, error) {
	return starlark.String(p).Hash()
}

func (p StarlarkPath) CompareSameType(op starsyntax.Token, y_ starlark.Value, depth int) (bool, error) {
	y := y_.(StarlarkPath)

	switch op {
	case starsyntax.EQL:
		return p == y, nil
	case starsyntax.NEQ:
		return p != y, nil
	case starsyntax.LT:
		return p < y, nil
	case starsyntax.LE:
		return p <= y, nil
	case starsyntax.GT:
		return p > y, nil
	case starsyntax.GE:
		return p >= y, nil
	}

	return false, eris.Errorf("unknown operator %v", op)
}

func (p StarlarkPath) Index(i int) starlark.Value {
	return starlark.String(p[i])
}

func (p StarlarkPath) Len() int {
	return len(p)
}

func (p StarlarkPath) Slice(start, end, step int) starlark.Value {
	return starlark.String(p).Slice(start, end, step)
}
