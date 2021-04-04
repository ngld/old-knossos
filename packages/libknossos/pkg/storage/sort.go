package storage

import (
	"sort"

	"github.com/Masterminds/semver/v3"
)

// StringVersionCollection can be used to sort a string slice based on semver ordering rules
type StringVersionCollection struct {
	versions        []string
	decodedVersions []*semver.Version
}

var _ sort.Interface = (*StringVersionCollection)(nil)

func (c StringVersionCollection) Len() int { return len(c.versions) }
func (c *StringVersionCollection) Swap(i, j int) {
	c.versions[i], c.versions[j] = c.versions[j], c.versions[i]
	c.decodedVersions[i], c.decodedVersions[j] = c.decodedVersions[j], c.decodedVersions[i]
}

func (c StringVersionCollection) Less(i, j int) bool {
	return c.decodedVersions[i].LessThan(c.decodedVersions[j])
}

// NewStringVersionCollection wraps the passed versions in a StringVersionCollection which can then be passed to sort.Sort
func NewStringVersionCollection(versions []string) (*StringVersionCollection, error) {
	decodedVersions := make([]*semver.Version, len(versions))
	for idx, strVer := range versions {
		ver, err := semver.NewVersion(strVer)
		if err != nil {
			return nil, err
		}

		decodedVersions[idx] = ver
	}

	return &StringVersionCollection{
		versions:        versions,
		decodedVersions: decodedVersions,
	}, nil
}
