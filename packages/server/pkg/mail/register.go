package mail

import (
	"context"
	"crypto/tls"
	"fmt"
	ht "html/template"
	"io/ioutil"
	"net/smtp"
	"strings"
	tt "text/template"

	"github.com/jordan-wright/email"
	"github.com/rotisserie/eris"

	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
)

// RegMailParams contains the values that will be passed to the mail template
type RegMailParams struct {
	To       string
	Username string
	Token    string
	// This field will be set automatically
	BaseURL string
}

var (
	regText *tt.Template
	regHTML *ht.Template
)

func initReg(cfg *config.Config) error {
	data, err := ioutil.ReadFile(cfg.Mail.Register.Text)
	if err != nil {
		return eris.Wrapf(err, "failed to read template file %s", cfg.Mail.Register.Text)
	}

	regText, err = tt.New("registration mail template").Parse(string(data))
	if err != nil {
		return eris.Wrapf(err, "failed to parse template %s", cfg.Mail.Register.Text)
	}

	data, err = ioutil.ReadFile(cfg.Mail.Register.HTML)
	if err != nil {
		return eris.Wrapf(err, "failed to read template file %s", cfg.Mail.Register.HTML)
	}

	regHTML, err = ht.New("registration mail html").Parse(string(data))
	if err != nil {
		return eris.Wrapf(err, "failed to parse template %s", cfg.Mail.Register.HTML)
	}

	return nil
}

// SendRegistrationMail sends a registration mail
func SendRegistrationMail(ctx context.Context, cfg *config.Config, params RegMailParams) error {
	nblog.Log(ctx).Debug().Msgf("Sending registration mail to %s", params.To)

	params.BaseURL = cfg.HTTP.BaseURL

	mail := email.NewEmail()
	mail.From = cfg.Mail.From
	mail.Subject = cfg.Mail.Register.Subject
	mail.To = []string{params.To}

	text := strings.Builder{}
	err := regText.Execute(&text, params)
	if err != nil {
		return eris.Wrap(err, "failed to execute registration text template")
	}

	mail.Text = []byte(text.String())

	text.Reset()
	err = regHTML.Execute(&text, params)
	if err != nil {
		return eris.Wrap(err, "failed to execute registration HTML template")
	}

	mail.HTML = []byte(text.String())

	auth := smtp.PlainAuth("", cfg.Mail.Username, cfg.Mail.Password, cfg.Mail.Server)
	addr := fmt.Sprintf("%s:%d", cfg.Mail.Server, cfg.Mail.Port)

	if cfg.Mail.Encryption == "STARTTLS" {
		err = mail.SendWithStartTLS(addr, auth, &tls.Config{
			ServerName: cfg.Mail.Server,
		})
	} else if cfg.Mail.Encryption == "SSL" {
		err = mail.SendWithTLS(addr, auth, &tls.Config{
			ServerName: cfg.Mail.Server,
		})
	} else {
		err = mail.Send(addr, auth)
	}

	if err != nil {
		return eris.Wrap(err, "failed to send mail")
	}

	nblog.Log(ctx).Debug().Msg("Mail successfully sent")
	return nil
}
