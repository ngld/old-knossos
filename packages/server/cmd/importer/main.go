package main

import (
	"context"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/aidarkhanov/nanoid"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/rotisserie/eris"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/db"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/ngld/knossos/packages/server/pkg/importer"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
)

func handleFile(ctx context.Context, q *queries.DBQuerier, url string) int32 {
	if url == "" {
		return 0
	}

	fid, err := q.CreateExternalFile(ctx, queries.CreateExternalFileParams{
		StorageKey: "ext#" + nanoid.New(),
		Filesize:   0,
		Public:     true,
		External:   []string{url},
		Owner:      1,
	})
	if err != nil {
		log.Fatal().Err(err).Msgf("Failed to store external file %s.", url)
	}

	return fid
}

type FilesSource struct {
	packageID int32
	files     []importer.KnFile
	curIdx    int
	length    int
	err       error
}

func (fs *FilesSource) Next() bool {
	fs.curIdx++
	return fs.err == nil && fs.curIdx < fs.length
}

var filesSourceCols = []string{"package_id", "path", "archive", "archive_path", "checksum_algo", "checksum_digest"}

func (fs *FilesSource) Values() ([]interface{}, error) {
	file := fs.files[fs.curIdx]

	digest, err := hex.DecodeString(file.Checksum[1])
	if err != nil {
		fs.err = err
		return nil, err
	}

	result := make([]interface{}, 6)
	result[0] = fs.packageID
	result[1] = file.Filename
	result[2] = file.Archive
	result[3] = file.OrigName
	result[4] = file.Checksum[0]
	result[5] = digest

	return result, nil
}

func (fs *FilesSource) Err() error {
	return fs.err
}

func CopyFromFiles(ctx context.Context, tx pgx.Tx, pkg int32, files []importer.KnFile) (int64, error) {
	source := FilesSource{
		packageID: pkg,
		files:     files,
		curIdx:    -1,
		length:    len(files),
		err:       nil,
	}

	return tx.CopyFrom(ctx, pgx.Identifier{"mod_package_files"}, filesSourceCols, &source)
}

func main() {
	cfg, loader := config.Loader()
	// flags := loader.Flags()

	if err := loader.Load(); err != nil {
		if strings.Contains(err.Error(), "help requested") {
			os.Exit(3)
		}

		panic(err)
	}

	writer := zerolog.ConsoleWriter{Out: os.Stdout}
	writer.TimeFormat = "02.01.2006 15:04:05 MST"
	writer.FormatFieldValue = func(value interface{}) string {
		if value == nil {
			return "                "
		}

		str, ok := value.(string)
		if ok {
			if len(str) == 16 {
				// color request IDs in cyan  we have to guess based on the field content because we can't get
				// the current field name
				return fmt.Sprintf("\x1b[%dm%s\x1b[0m", 36, value)
			} else if strings.Contains(str, "\\n") && strings.Contains(str, "\\t") {
				// unquote values that contain line breaks and tabs because they're most likely stack traces
				str, err := strconv.Unquote(str)
				if err == nil {
					return str
				}
			}
		}

		return fmt.Sprintf("%s", value)
	}

	log.Logger = log.Output(writer)

	zerolog.ErrorStackMarshaler = func(err error) interface{} {
		return eris.ToString(err, true)
	}

	if err := cfg.Validate(); err != nil {
		log.Fatal().Err(err).Msg("Failed to parse config")
	}

	zerolog.SetGlobalLevel(cfg.LogLevel())
	log.Logger = log.Logger.With().Caller().Stack().Logger()

	dbConfig, err := pgxpool.ParseConfig(cfg.Database)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to parse DB config")
	}

	dbConfig.ConnConfig.Logger = nblog.PgxLogger{}
	dbConfig.ConnConfig.LogLevel = pgx.LogLevelDebug
	pool, err := pgxpool.ConnectConfig(context.Background(), dbConfig)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to open DB connection")
	}

	log.Info().Msg("Finished parsing configuration; loading data")

	inFile, err := os.Open("repo.json")
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to open repo.json")
	}
	defer inFile.Close()

	jsonStr, err := ioutil.ReadAll(inFile)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to read repo.json")
	}

	data := importer.KnStruct{}
	err = json.Unmarshal(jsonStr, &data)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to parse repo.json")
	}

	typeMap := map[string]db.ModType{
		"mod":    db.TypeMod,
		"tc":     db.TypeTotalConversion,
		"engine": db.TypeEngine,
		"tool":   db.TypeTool,
		"ext":    db.TypeExtension,
	}

	stabilityMap := map[string]db.EngineStability{
		"":        db.EngineUnknown,
		"stable":  db.EngineStable,
		"rc":      db.EngineRC,
		"nightly": db.EngineNightly,
	}

	pkgTypeMap := map[string]db.PackageType{
		"required":    db.PackageRequired,
		"recommended": db.PackageRecommended,
		"optional":    db.PackageOptional,
	}

	ctx := context.Background()
	tx, err := pool.Begin(ctx)
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to initiate transaction")
	}

	_, err = tx.Exec(ctx, "SET CONSTRAINTS ALL DEFERRED")
	if err != nil {
		log.Fatal().Err(err).Msg("Failed to setup the transaction")
	}

	q := queries.NewQuerier(tx)

	count := len(data.Mods)
	aidCache := map[string]int32{}
	for i, mod := range data.Mods {
		log.Info().Msgf("Mod %4d of %d", i, count)

		aid, ok := aidCache[mod.ID]
		if !ok {
			mType, ok := typeMap[mod.Type]
			if !ok {
				log.Warn().Msgf("Invalid mod type %s detected for mod %s (%s)", mod.Type, mod.Title, mod.ID)
				mType = db.TypeMod
			}

			aid, err = q.CreateMod(ctx, queries.CreateModParams{
				Modid: mod.ID,
				Title: mod.Title,
				Type:  int16(mType),
			})
			if err != nil {
				log.Fatal().Err(err).Msgf("Failed to insert mod %s (%s)", mod.Title, mod.ID)
			}

			aidCache[mod.ID] = aid
		}

		log.Info().Msgf("AID %d", aid)

		rStabilility, ok := stabilityMap[mod.Stability]
		if !ok {
			log.Warn().Msgf("Invalid stability %s detected for mod %s (%s)", mod.Stability, mod.ID, mod.Version)
			rStabilility = db.EngineUnknown
		}

		// TODO files (logo -> ?, tile -> teaser, banner -> banner, screenshots)
		relDate, err := time.Parse("2006-01-02T15:04:05Z", mod.FirstRelease)
		if err != nil {
			if mod.FirstRelease == "" {
				relDate = time.Unix(1, 0)
			} else {
				log.Fatal().Msgf("Invalid release date for mod %s (%s): %s", mod.ID, mod.Version, mod.FirstRelease)
			}
		}

		updateDate, err := time.Parse("2006-01-02T15:04:05Z", mod.LastUpdate)
		if err != nil {
			if mod.LastUpdate == "" {
				updateDate = time.Unix(1, 0)
			} else {
				log.Fatal().Msgf("Invalid update date for mod %s (%s): %s", mod.ID, mod.Version, mod.LastUpdate)
			}
		}

		screens := make([]int32, len(mod.Screenshots))
		for idx, url := range mod.Screenshots {
			screens[idx] = handleFile(ctx, q, url)
		}

		modParams := queries.CreateReleaseParams{
			ModAid:        aid,
			Version:       mod.Version,
			Stability:     int16(rStabilility),
			Description:   mod.Description,
			ReleaseThread: mod.ReleaseThread,
			Videos:        mod.Videos,
			Notes:         mod.Notes,
			Cmdline:       mod.Cmdline,
			Screenshots:   screens,
			Teaser:        handleFile(ctx, q, mod.Tile),
			Banner:        handleFile(ctx, q, mod.Banner),
		}

		modParams.Released.Set(relDate)
		modParams.Updated.Set(updateDate)

		rid, err := q.CreateRelease(ctx, modParams)
		if err != nil {
			log.Fatal().Err(err).Msgf("Failed to insert release %s (%s)", mod.ID, mod.Version)
		}

		for _, pkg := range mod.Packages {
			pkgType, ok := pkgTypeMap[pkg.Status]
			if !ok {
				log.Fatal().Msgf("Failed to parse package status %s for %s in %s (%s)", pkg.Status, pkg.Name, mod.ID, mod.Version)
			}

			pid, err := q.CreatePackage(ctx, queries.CreatePackageParams{
				ReleaseID: rid,
				Name:      pkg.Name,
				Folder:    pkg.Folder,
				Notes:     pkg.Notes,
				Type:      int16(pkgType),
				// TODO: Actually parse the env spec
				CpuSpecs:  strings.Split(pkg.Environment, " && "),
				KnossosVp: pkg.IsVp,
			})
			if err != nil {
				log.Fatal().Err(err).Msgf("Failed to insert package %s for %s (%s)", pkg.Name, mod.ID, mod.Version)
			}

			pkgBatch := new(pgx.Batch)

			for _, dep := range pkg.Dependencies {
				q.CreatePackageDependencyBatch(pkgBatch, queries.CreatePackageDependencyParams{
					PackageID: pid,
					Modid:     dep.ID,
					Version:   dep.Version,
					Packages:  dep.Packages,
				})
			}

			for _, exe := range pkg.Executables {
				prio := int16(0)
				// See https://github.com/ngld/knossos/blob/1f60d925498c02d3db76a54d3ee20c31b75c5a21/knossos/repo.py#L35-L40
				if exe.Properties.X64 {
					prio += 50
				}
				if exe.Properties.AVX2 {
					prio += 3
				}
				if exe.Properties.AVX {
					prio += 2
				}
				if exe.Properties.SSE2 {
					prio++
				}

				q.CreatePackageExecutableBatch(pkgBatch, queries.CreatePackageExecutableParams{
					PackageID: pid,
					Path:      exe.File,
					Label:     exe.Label,
					Priority:  prio,
					Debug:     strings.Contains(exe.Label, "Debug"),
				})
			}

			for _, archive := range pkg.Files {
				digest, err := hex.DecodeString(archive.Checksum[1])
				if err != nil {
					log.Fatal().Err(err).Msgf("Failed to parse digest for archive %s of %s for %s (%s)", archive.Filename, pkg.Name, mod.ID, mod.Version)
				}

				fid, err := q.CreateExternalFile(ctx, queries.CreateExternalFileParams{
					StorageKey: "ext#" + nanoid.New(),
					Filesize:   int32(archive.FileSize),
					Public:     true,
					External:   archive.URLs,
					Owner:      1,
				})
				if err != nil {
					log.Fatal().Err(err).Msgf("Failed to index file for archive %s of %s for %s (%s)", archive.Filename, pkg.Name, mod.ID, mod.Version)
				}

				q.CreatePackageArchiveBatch(pkgBatch, queries.CreatePackageArchiveParams{
					PackageID:      pid,
					Label:          archive.Filename,
					Destination:    archive.Dest,
					ChecksumAlgo:   archive.Checksum[0],
					ChecksumDigest: digest,
					FileID:         fid,
				})
			}

			count, err := CopyFromFiles(ctx, tx, pid, pkg.Filelist)
			if err != nil {
				log.Fatal().Err(err).Msgf("Failed to process filelist on %s for %s (%s)", pkg.Name, mod.ID, mod.Version)
			}
			if count != int64(len(pkg.Filelist)) {
				log.Fatal().Err(err).Msgf("Imported only %d of %d files on %s for %s (%s)", count, len(pkg.Filelist), pkg.Name, mod.ID, mod.Version)
			}

			batchResults := tx.SendBatch(ctx, pkgBatch)
			for idx := 0; idx < pkgBatch.Len(); idx++ {
				_, err := batchResults.Exec()
				if err != nil {
					log.Fatal().Err(err).Msgf("Failed process package contents for %s of %s (%s)", pkg.Name, mod.ID, mod.Version)
				}
			}
			batchResults.Close()
		}
	}

	log.Info().Msg("Comitting")
	err = tx.Commit(ctx)
	if err != nil {
		log.Fatal().Err(err).Msg("Commit failed")
	}

	log.Info().Msg("Done")
}
