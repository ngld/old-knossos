package config

import (
	"github.com/cristalhq/aconfig"
	"github.com/cristalhq/aconfig/aconfigtoml"
	"github.com/jackc/pgx/v4/pgxpool"
	"github.com/rotisserie/eris"
	"github.com/rs/zerolog"
)

// Config describes all configuration options
type Config struct {
	Database string `default:"pgsql://localhost/nebula" usage:"PostgreSQL DSN to connect to (i.e. pgsql://localhost/nebula)"`
	Log      struct {
		Level string `default:"info"`
		File  string
		JSON  bool `default:"false" usage:"Output JSONND instead of pretty console messages"`
	}
	HTTP struct {
		Address string `default:"127.0.0.1:8080" usage:"Adress to listen on"`
		BaseURL string `default:"http://example.com" usage:"Public URL for this server"`
	}
	Argon2 struct {
		Memory      uint32 `default:"65536"`
		Iterations  uint32 `default:"3"`
		Parallelism uint8  `default:"2"`
		SaltLength  uint32 `default:"16"`
		KeyLength   uint32 `default:"32"`
	}
	Mail struct {
		From       string `usage:"Mail sender"`
		Server     string `usage:"SMTP server"`
		Port       int
		Encryption string `default:"STARTTLS" usage:"Transport encryption (STARTTLS, SSL or None)"`
		Username   string
		Password   string

		Register struct {
			Subject string `default:"[FSNebula] Welcome!" usage:"Registration mail subject"`
			Text    string `usage:"Text template for the registration mail"`
			HTML    string `usage:"HTML template for the registration mail"`
		}

		Reset struct {
			Subject string `default:"[FSNebula] Password reset" usage:"Password reset subject"`
			Text    string `usage:"Text template for the password reset mail"`
			HTML    string `usage:"HTML template for the password reset mail"`
		}
	}
}

var logLevels = map[string]zerolog.Level{
	"debug":   zerolog.DebugLevel,
	"info":    zerolog.InfoLevel,
	"warn":    zerolog.WarnLevel,
	"warning": zerolog.WarnLevel,
	"error":   zerolog.ErrorLevel,
	"fatal":   zerolog.FatalLevel,
}

// Loader initializes an empty config object and returns a new Loader for this object
func Loader() (*Config, *aconfig.Loader) {
	cfg := Config{}
	return &cfg, aconfig.LoaderFor(&cfg, aconfig.Config{
		EnvPrefix:  "NEBULA",
		FlagPrefix: "cfg",
		Files:      []string{"config.toml"},
		FileDecoders: map[string]aconfig.FileDecoder{
			".toml": aconfigtoml.New(),
		},
	})
}

// Validate verifies that all config fields have valid values
func (cfg *Config) Validate() error {
	_, err := pgxpool.ParseConfig(cfg.Database)
	if err != nil {
		return eris.Wrapf(err, `Invalid value for database`)
	}

	_, ok := logLevels[cfg.Log.Level]
	if !ok {
		return eris.Errorf(`Invalid value for log.level: %s`, cfg.Log.Level)
	}

	switch cfg.Mail.Encryption {
	case "STARTTLS":
	case "SSL":
	case "None":
		// valid
		break
	default:
		return eris.Errorf(`Invalid value for mail.encryption: %s (must be one of STARTTLS, SSL or None)`, cfg.Mail.Encryption)
	}

	return nil
}

// LogLevel converts the .Log.Level field to a zerolog.Level
func (cfg *Config) LogLevel() zerolog.Level {
	return logLevels[cfg.Log.Level]
}
