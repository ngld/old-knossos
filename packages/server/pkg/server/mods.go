package server

import (
	"context"

	"github.com/jackc/pgtype"
	"github.com/ngld/knossos/packages/api/api"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
	"github.com/twitchtv/twirp"
)

func (neb nebula) GetModList(ctx context.Context, req *api.ModListRequest) (*api.ModListResponse, error) {
	limit := int(req.Limit)
	if limit > 100 {
		limit = 100
	}
	mods, err := neb.Q.GetPublicMods(ctx, limit, int(req.Offset))
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to fetch public mod list")
		return nil, twirp.InternalError("internal error")
	}

	modCount, err := neb.Q.GetPublicModCount(ctx)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to fetch public mod count")
		return nil, twirp.InternalError("internal error")
	}

	modItems := make([]*api.ModListItem, len(mods))
	for idx, mod := range mods {
		teaserURL := ""
		if mod.StorageKey.Status == pgtype.Present {
			if mod.External.Status == pgtype.Present {
				teaserURL = mod.External.Elements[0].String
			} else {
				nblog.Log(ctx).Warn().Msgf("Generating teaser URLs is not yet supported (%s)", mod.StorageKey.String)
			}
		}

		modItems[idx] = &api.ModListItem{
			Modid:        mod.Modid.String,
			Teaser:       teaserURL,
			Title:        mod.Title.String,
			ReleaseCount: uint32(mod.ReleaseCount.Int),
		}
	}

	return &api.ModListResponse{
		Count: int32(modCount.Int),
		Mods:  modItems,
	}, nil
}

// GetModDetails retrieves details for the given mod and returns them
func (neb nebula) GetModDetails(ctx context.Context, req *api.ModDetailsRequest) (*api.ModDetailsResponse, error) {
	// details, err := neb.Q.Get
	return nil, nil
}
