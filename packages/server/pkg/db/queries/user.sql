-- name: GetLoginDetails :one
SELECT id, password, role FROM users WHERE username = pggen.arg('username') AND validated = true LIMIT 1;

-- name: GetUser :one
SELECT * FROM users WHERE username = pggen.arg('username') LIMIT 1;

-- name: GetUserByID :one
SELECT * FROM users WHERE id = pggen.arg('id') LIMIT 1;

-- name: GetUserByEmail :one
SELECT * FROM users WHERE email = pggen.arg('email') LIMIT 1;

-- name: CreateUser :one
INSERT INTO users (username, email, password, role, reset_token)
    VALUES (pggen.arg('username'), pggen.arg('email'), pggen.arg('password'), pggen.arg('role'), pggen.arg('reset_token'))
    RETURNING (id);

-- name: GetUserByResetToken :one
SELECT * FROM users WHERE reset_token = pggen.arg('token') LIMIT 1;

-- name: ValidateUser :exec
UPDATE users SET validated = true, reset_token = '' WHERE id = pggen.arg('id');

-- name: SetResetToken :exec
UPDATE users SET reset_token = pggen.arg('token'), password = '' WHERE id = pggen.arg('id');

-- name: SetPassword :exec
UPDATE users SET password = pggen.arg('password'), reset_token = '' WHERE id = pggen.arg('id');

-- name: SetPasswordByResetToken :exec
UPDATE users SET password = pggen.arg('password'), reset_token = '' WHERE reset_token = pggen.arg('token');
