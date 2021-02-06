package mail

import (
	"github.com/ngld/knossos/packages/server/pkg/config"
)

// Init configuration based parts of the mail package
func Init(cfg *config.Config) error {
	err := initReg(cfg)
	if err != nil {
		return err
	}

	err = initReset(cfg)
	if err != nil {
		return err
	}

	return nil
}
