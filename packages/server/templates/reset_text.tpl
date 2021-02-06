{{if .Found}}
Hi {{.Username}},

apparently you tried to reset your password at fsnebula.org. If you didn't, feel free to ignore this mail.

If you *did* try to reset your password at fsnebula.org, please follow this link to finish that process:
{{.BaseURL}}/mail/reset/{{.Token}}

Have a nice day,
your FSNebula team (AKA ngld)
{{else}}
Hi,

apparently you tried to reset your password at fsnebula.org. However, we don't have an account for this email address.

Please make sure that you entered the email you signed up with or create a new account.

Have a nice day,
your FSNebula team (AKA ngld)
{{end}}
