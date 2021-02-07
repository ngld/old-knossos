package server

import (
	"context"
	"encoding/hex"

	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4"
	"github.com/ngld/knossos/packages/api/api"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
	"github.com/rotisserie/eris"
	"github.com/twitchtv/twirp"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func GetFileURL(ctx context.Context, q *queries.DBQuerier, fid int) (string, error) {
	data, err := q.GetPublicFileByID(ctx, int32(fid))
	if err != nil {
		return "", eris.Wrapf(err, "failed to fetch file %d", fid)
	}

	if data.StorageKey.Status == pgtype.Present {
		if data.External.Status == pgtype.Present {
			return data.External.Elements[0].String, nil
		} else {
			nblog.Log(ctx).Warn().Msgf("Generating teaser URLs is not yet supported (%s)", data.StorageKey.String)
			return "", nil
		}
	}
	return "", nil
}

func (neb nebula) GetModList(ctx context.Context, req *api.ModListRequest) (*api.ModListResponse, error) {
	limit := int(req.Limit)
	if limit > 300 {
		limit = 300
	}

	var mods []queries.GetPublicModsRow
	var err error

	if req.Query == "" {
		mods, err = neb.Q.GetPublicMods(ctx, limit, int(req.Offset))
	} else {
		sRes, sErr := neb.Q.SearchPublicMods(ctx, queries.SearchPublicModsParams{
			Limit:  int(req.Limit),
			Offset: int(req.Offset),
			Query:  req.Query,
		})

		err = sErr
		mods = make([]queries.GetPublicModsRow, len(sRes))
		for idx, row := range sRes {
			mods[idx] = queries.GetPublicModsRow{
				Aid:          row.Aid,
				Title:        row.Title,
				Type:         row.Type,
				ReleaseCount: row.ReleaseCount,
				StorageKey:   row.StorageKey,
				External:     row.External,
			}
		}
	}
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
	if req.Modid == "" {
		return nil, twirp.RequiredArgumentError("Modid")
	}
	if req.Version == "" && !req.Latest {
		return nil, twirp.RequiredArgumentError("Version")
	}

	if req.Latest {
		version, err := neb.Q.GetLatestPublicModVersion(ctx, req.Modid)
		if err != nil {
			if eris.Is(err, pgx.ErrNoRows) {
				return nil, twirp.NotFoundError("no such mod")
			}

			nblog.Log(ctx).Error().Err(err).Msgf("Failed to determine latest version for mod %s", req.Modid)
			return nil, twirp.InternalError("internal error")
		}

		req.Version = version.Version.String
	}

	details, err := neb.Q.GetPublicReleaseByModVersion(ctx, req.Modid, req.Version)
	if err != nil {
		if eris.Is(err, pgx.ErrNoRows) {
			return nil, twirp.NotFoundError("no such mod")
		}

		nblog.Log(ctx).Error().Err(err).Msgf("Failed to fetch data for public release %s (%s)", req.Modid, req.Version)
		return nil, twirp.InternalError("internal error")
	}

	bannerURL, err := GetFileURL(ctx, neb.Q, int(details.Banner.Int))
	if err != nil {
		return nil, twirp.InternalError("internal error")
	}

	screenshotURLs := make([]string, len(details.Screenshots.Elements))
	for idx, fid := range details.Screenshots.Elements {
		screenshotURLs[idx], err = GetFileURL(ctx, neb.Q, int(fid.Int))
		if err != nil {
			return nil, twirp.InternalError("internal error")
		}
	}

	videos := make([]string, len(details.Videos.Elements))
	for idx, video := range details.Videos.Elements {
		videos[idx] = video.String
	}

	result := &api.ModDetailsResponse{
		Title:         details.Title.String,
		Version:       details.Version.String,
		Type:          uint32(details.Type.Int),
		Stability:     uint32(details.Stability.Int),
		Description:   details.Description.String,
		Banner:        bannerURL,
		ReleaseThread: details.ReleaseThread.String,
		Screenshots:   screenshotURLs,
		Videos:        videos,
		Released:      &timestamppb.Timestamp{Seconds: details.Released.Time.Unix()},
		Updated:       &timestamppb.Timestamp{Seconds: details.Updated.Time.Unix()},
	}

	result.Versions, err = neb.Q.GetPublicModVersions(ctx, details.Aid.Int)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msgf("Failed to fetch version list for mod %d", details.Aid.Int)
		return nil, twirp.InternalError("internal error")
	}

	if req.RequestDownloads {
		dlInfos, err := neb.Q.GetPublicDownloadsByRID(ctx, details.ID.Int)
		if err != nil {
			nblog.Log(ctx).Error().Err(err).Msg("Failed to fetch download info")
		} else {
			packages := map[string]*[]*api.ModDownloadArchive{}
			result.Downloads = make([]*api.ModDownloadPackage, 0)

			for _, row := range dlInfos {
				archives, found := packages[row.Package.String]
				if !found {
					apiPkg := &api.ModDownloadPackage{
						Name:     row.Package.String,
						Notes:    row.PackageNotes.String,
						Archives: make([]*api.ModDownloadArchive, 0),
					}

					result.Downloads = append(result.Downloads, apiPkg)
					packages[row.Package.String] = &apiPkg.Archives
					archives = &apiPkg.Archives
				}

				archive := &api.ModDownloadArchive{
					Label:    row.Label.String,
					Checksum: hex.EncodeToString(row.ChecksumDigest.Bytes),
					Size:     uint32(row.Filesize.Int),
					// TODO support internal links
					Links: make([]string, len(row.External.Elements)),
				}

				for idx, link := range row.External.Elements {
					archive.Links[idx] = link.String
				}

				*archives = append(*archives, archive)
			}
		}
	}

	return result, nil
}
