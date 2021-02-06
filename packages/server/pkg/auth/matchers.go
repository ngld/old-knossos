package auth

import (
	"context"
	"time"

	"github.com/rotisserie/eris"
	"github.com/zpatrick/rbac"

	"github.com/ngld/knossos/packages/server/pkg/db"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
)

// ErrInvalidTarget is returned if the target doesn't follow the expected format
var ErrInvalidTarget = eris.New("invalid target")

type Bag struct{}

type ModBag struct {
	Bag
	UserID         int
	ModID          string
	ReleaseVersion string
}

func publicMod(q *queries.DBQuerier) rbac.Matcher {
	return func(target string) (bool, error) {
		bag := ModBag{}
		if err := UnmarshalBag(target, &bag); err != nil {
			return false, eris.Wrapf(err, "failed to parse target")
		}

		if bag.ReleaseVersion != "" {
			// releases need further checks
			return false, nil
		}

		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		private, err := q.GetModVisibility(ctx, bag.ModID)
		if err != nil {
			return false, eris.Wrapf(err, "failed to retrieve mod role")
		}

		return !private.Bool, nil
	}
}

func publicRelease(q *queries.DBQuerier) rbac.Matcher {
	return func(target string) (bool, error) {
		bag := ModBag{}
		if err := UnmarshalBag(target, &bag); err != nil {
			return false, eris.Wrapf(err, "failed to parse target")
		}

		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		row, err := q.GetReleaseVisibility(ctx, bag.ModID, bag.ReleaseVersion)
		if err != nil {
			return false, eris.Wrapf(err, "failed to retrieve release visibility")
		}

		return !row.Mod.Bool && !row.Release.Bool, nil
	}
}

func modRole(q *queries.DBQuerier, matchRoles []db.ModRole) rbac.Matcher {
	return func(target string) (bool, error) {
		bag := ModBag{}
		if err := UnmarshalBag(target, &bag); err != nil {
			return false, eris.Wrapf(err, "failed to parse target")
		}

		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()

		role, err := q.GetModRoleByModID(ctx, bag.ModID, int32(bag.UserID))
		if err != nil {
			return false, eris.Wrapf(err, "failed to retrieve mod role")
		}

		dbRole := db.ModRole(role.Int)
		for _, match := range matchRoles {
			if dbRole == match {
				return true, nil
			}
		}
		return false, nil
	}
}

type UserBag struct {
	Bag
	CurrentUser int
	TargetUser  int
}

func userSelf(q *queries.DBQuerier) rbac.Matcher {
	return func(target string) (bool, error) {
		bag := UserBag{}
		if err := UnmarshalBag(target, &bag); err != nil {
			return false, eris.Wrapf(err, "failed to parse target")
		}

		return bag.CurrentUser == bag.TargetUser, nil
	}
}
