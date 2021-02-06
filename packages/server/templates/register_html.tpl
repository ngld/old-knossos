<!DOCTYPE html>
<html>
  <head>
    <title>Register</title>
	<style type="text/css">
		/* TODO */
	</style>
  </head>
  <body>
<p>Hi {{.Username}},</p>

<p>
  apparently you attempted to register at <a href="https://fsnebula.org">fsnebula.org</a>.
  If you didn't, feel free to ignore this mail.
</p>

<p>
	If you <b>did</b> register at fsnebula.org, please follow this link to confirm your email address:<br>
	<a href="{{.BaseURL}}/mail/register/{{.Token}}">{{.BaseURL}}/mail/register/{{.Token}}</a>
</p>

<p>
	Have a nice day,<br>
	your FSNebula team (AKA ngld)
</p>
  </body>
</html>
