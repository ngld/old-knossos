package mail

import (
	"context"
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

// ResetMailParams contains the values that will be passed to the mail template
type ResetMailParams struct {
	To       string
	Found    bool
	Username string
	Token    string
	// This field will be set automatically
	BaseURL string
}

var resetText *tt.Template
var resetHTML *ht.Template

func initReset(cfg *config.Config) error {
	data, err := ioutil.ReadFile(cfg.Mail.Reset.Text)
	if err != nil {
		return eris.Wrapf(err, "failed to read template file %s", cfg.Mail.Reset.Text)
	}

	resetText, err = tt.New("reset mail template").Parse(string(data))
	if err != nil {
		return eris.Wrapf(err, "failed to parse template %s", cfg.Mail.Reset.Text)
	}

	data, err = ioutil.ReadFile(cfg.Mail.Reset.HTML)
	if err != nil {
		return eris.Wrapf(err, "failed to read template file %s", cfg.Mail.Reset.HTML)
	}

	resetHTML, err = ht.New("reset mail html").Parse(string(data))
	if err != nil {
		return eris.Wrapf(err, "failed to parse template %s", cfg.Mail.Reset.HTML)
	}

	return nil
}

// SendResetMail sends a password reset mail
func SendResetMail(ctx context.Context, cfg *config.Config, params ResetMailParams) error {
	nblog.Log(ctx).Debug().Msgf("Sending reset mail to %s", params.To)

	params.BaseURL = cfg.HTTP.BaseURL

	mail := email.NewEmail()
	mail.From = cfg.Mail.From
	mail.Subject = cfg.Mail.Reset.Subject
	mail.To = []string{params.To}

	text := strings.Builder{}
	err := resetText.Execute(&text, params)
	if err != nil {
		return eris.Wrap(err, "failed to execute password reset text template")
	}

	mail.Text = []byte(text.String())

	text.Reset()
	err = resetHTML.Execute(&text, params)
	if err != nil {
		return eris.Wrap(err, "failed to execute password reset HTML template")
	}

	mail.HTML = []byte(text.String())

	auth := smtp.PlainAuth("", cfg.Mail.Username, cfg.Mail.Password, cfg.Mail.Server)
	addr := fmt.Sprintf("%s:%d", cfg.Mail.Server, cfg.Mail.Port)

	if cfg.Mail.Encryption == "STARTTLS" {
		err = mail.SendWithStartTLS(addr, auth, nil)
	} else if cfg.Mail.Encryption == "SSL" {
		err = mail.SendWithTLS(addr, auth, nil)
	} else {
		err = mail.Send(addr, auth)
	}

	if err != nil {
		return eris.Wrap(err, "failed to send mail")
	}

	nblog.Log(ctx).Debug().Msg("Mail successfully sent")
	return nil
}
