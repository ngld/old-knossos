module github.com/ngld/knossos/packages/server

go 1.15

require (
	github.com/aidarkhanov/nanoid v1.0.8
	github.com/alecthomas/units v0.0.0-20201120081800-1786d5ef83d4 // indirect
	github.com/andskur/argon2-hashing v0.1.3
	github.com/cortesi/modd v0.0.0-20200630120222-8983974e5450
	github.com/cristalhq/aconfig v0.10.1
	github.com/cristalhq/aconfig/aconfigtoml v0.11.0
	github.com/dgrijalva/jwt-go/v4 v4.0.0-preview1
	github.com/docker/docker v20.10.3+incompatible // indirect
	github.com/fatih/color v1.10.0 // indirect
	github.com/gorilla/mux v1.8.0
	github.com/jackc/pgconn v1.8.0
	github.com/jackc/pgproto3/v2 v2.0.7 // indirect
	github.com/jackc/pgtype v1.6.2
	github.com/jackc/pgx/v4 v4.10.1
	github.com/jordan-wright/email v4.0.1-0.20210109023952-943e75fe5223+incompatible
	github.com/jschaf/pggen v0.0.0-20210207090817-e6c5627c66c1
	github.com/lib/pq v1.9.0 // indirect
	github.com/ngld/knossos/packages/api v0.0.0-00010101000000-000000000000
	github.com/rotisserie/eris v0.5.0
	github.com/rs/zerolog v1.15.0
	github.com/ryanuber/go-glob v1.0.0 // indirect
	github.com/shaj13/go-guardian/v2 v2.6.0
	github.com/shaj13/libcache v1.0.0
	github.com/sirupsen/logrus v1.7.0 // indirect
	github.com/twitchtv/twirp v7.1.0+incompatible
	github.com/unrolled/secure v1.0.8
	github.com/zpatrick/rbac v0.0.0-20180829190353-d2c4f050cf28
	go.uber.org/multierr v1.6.0 // indirect
	go.uber.org/zap v1.16.0 // indirect
	golang.org/x/crypto v0.0.0-20201221181555-eec23a3978ad // indirect
	golang.org/x/mod v0.4.1 // indirect
	golang.org/x/net v0.0.0-20210119194325-5f4716e94777 // indirect
	golang.org/x/sync v0.0.0-20201207232520-09787c993a3a // indirect
	golang.org/x/sys v0.0.0-20210124154548-22da62e12c0c // indirect
	golang.org/x/term v0.0.0-20201210144234-2321bbc49cbf // indirect
	golang.org/x/text v0.3.5 // indirect
	google.golang.org/genproto v0.0.0-20210207032614-bba0dbe2a9ea // indirect
	google.golang.org/protobuf v1.25.0
	gopkg.in/yaml.v3 v3.0.0-20210107192922-496545a6307b // indirect
)

replace github.com/ngld/knossos/packages/api => ../api
