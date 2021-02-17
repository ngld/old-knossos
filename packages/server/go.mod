module github.com/ngld/knossos/packages/server

go 1.15

require (
	github.com/aidarkhanov/nanoid v1.0.8
	github.com/andskur/argon2-hashing v0.1.3
	github.com/cristalhq/aconfig v0.10.1
	github.com/cristalhq/aconfig/aconfigtoml v0.11.0
	github.com/dgrijalva/jwt-go/v4 v4.0.0-preview1
	github.com/google/go-cmp v0.5.4 // indirect
	github.com/gorilla/mux v1.8.0
	github.com/jackc/pgconn v1.8.0
	github.com/jackc/pgproto3/v2 v2.0.7 // indirect
	github.com/jackc/pgtype v1.6.2
	github.com/jackc/pgx/v4 v4.10.1
	github.com/jordan-wright/email v4.0.1-0.20210109023952-943e75fe5223+incompatible
	github.com/kr/text v0.2.0 // indirect
	github.com/lib/pq v1.9.0 // indirect
	github.com/ngld/knossos/packages/api v0.0.0-00010101000000-000000000000
	github.com/niemeyer/pretty v0.0.0-20200227124842-a10e7caefd8e // indirect
	github.com/rotisserie/eris v0.5.0
	github.com/rs/zerolog v1.15.0
	github.com/ryanuber/go-glob v1.0.0 // indirect
	github.com/shaj13/go-guardian/v2 v2.6.0
	github.com/shaj13/libcache v1.0.0
	github.com/twitchtv/twirp v7.1.0+incompatible
	github.com/unrolled/secure v1.0.8
	github.com/zpatrick/rbac v0.0.0-20180829190353-d2c4f050cf28
	golang.org/x/crypto v0.0.0-20201221181555-eec23a3978ad // indirect
	golang.org/x/sys v0.0.0-20210124154548-22da62e12c0c // indirect
	golang.org/x/text v0.3.5 // indirect
	golang.org/x/xerrors v0.0.0-20200804184101-5ec99f83aff1 // indirect
	google.golang.org/protobuf v1.25.0
	gopkg.in/check.v1 v1.0.0-20200227125254-8fa46927fb4f // indirect
	gopkg.in/yaml.v3 v3.0.0-20210107192922-496545a6307b // indirect
)

replace github.com/ngld/knossos/packages/api => ../api
