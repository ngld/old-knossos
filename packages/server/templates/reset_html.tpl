<!DOCTYPE html>
<html>
  <head>
    <title>Password Reset</title>
	<style type="text/css">
		/* TODO */
	</style>
  </head>
  <body>
{{if .Found}}
<p>Hi {{.Username}},</p>

<p>
  apparently you tried to reset your password at <a href="https://fsnebula.org">fsnebula.org</a>.
  If you didn't, feel free to ignore this mail.
</p>

<p>
  If you <b>did</b> try to reset your password at fsnebula.org, please follow this link to finish that process:<br>
  <a href="{{.BaseURL}}/mail/reset/{{.Token}}">{{.BaseURL}}/mail/reset/{{.Token}}</a>
</p>

<p>
  Have a nice day,<br>
  your FSNebula team (AKA ngld)
</p>
{{else}}
<p>Hi,</p>

<p>
  apparently you tried to reset your password at <a href="https://fsnebula.org">fsnebula.org</a>.
  However, we don't have an account for this email address.
</p>

<p>
  Please make sure that you entered the email you signed up with or create a new account.
</p>

<p>
  Have a nice day,<br>
  your FSNebula team (AKA ngld)
</p>
{{end}}
  </body>
</html>
