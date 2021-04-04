package mods

import "fmt"

type ModMissing struct {
	ModID   string
	Version string
}

var _ error = (*ModMissing)(nil)

func (e ModMissing) Error() string {
	return fmt.Sprintf("The mod %s (%s) is missing.", e.ModID, e.Version)
}

type PackageMissing struct {
	ModID   string
	Version string
	Package string
}

var _ error = (*PackageMissing)(nil)

func (e PackageMissing) Error() string {
	return fmt.Sprintf("The package %s for mod %s (%s) is missing.", e.Package, e.ModID, e.Version)
}
