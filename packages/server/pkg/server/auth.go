package server

import (
	"context"

	"github.com/aidarkhanov/nanoid"
	argon2 "github.com/andskur/argon2-hashing"
	"github.com/jackc/pgx/v4"
	"github.com/rotisserie/eris"
	"github.com/twitchtv/twirp"

	"github.com/ngld/knossos/packages/api/api"
	"github.com/ngld/knossos/packages/server/pkg/auth"
	"github.com/ngld/knossos/packages/server/pkg/config"
	"github.com/ngld/knossos/packages/server/pkg/db"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/ngld/knossos/packages/server/pkg/mail"
	"github.com/ngld/knossos/packages/server/pkg/nblog"
)

var roles = map[int16]string{
	1: "guest",
	2: "member",
	3: "moderator",
	4: "admin",
}

func hashPassword(password string, cfg *config.Config) ([]byte, error) {
	return argon2.GenerateFromPassword([]byte(password), (*argon2.Params)(&cfg.Argon2))
}

// Login processes a new login request and returns a valid token on success
func (neb nebula) Login(ctx context.Context, req *api.LoginRequest) (*api.LoginResponse, error) {
	if req.Username == "" {
		return nil, twirp.RequiredArgumentError("Username")
	}
	if req.Password == "" {
		return nil, twirp.RequiredArgumentError("Password")
	}

	nblog.Log(ctx).Debug().Msgf("Login from %s", req.Username)
	details, err := neb.Q.GetLoginDetails(ctx, req.Username)
	if eris.Is(err, pgx.ErrNoRows) {
		return &api.LoginResponse{Success: false}, nil
	}
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("unexpected DB error")
		return nil, err
	}

	err = argon2.CompareHashAndPassword(details.Password.Bytes, []byte(req.Password))
	switch err {
	case argon2.ErrMismatchedHashAndPassword:
		return &api.LoginResponse{Success: false}, nil

	case nil:
		break

	case argon2.ErrInvalidHash:
	case argon2.ErrIncompatibleVersion:
		nblog.Log(ctx).Error().Err(err).Msg("Failed to process login request")
		return nil, twirp.InternalError("internal error")

	case argon2.ErrInvalidParams:
		nblog.Log(ctx).Error().Err(err).Msg("Failed to process login due to hashing misconfiguration")
		return nil, twirp.InternalError("internal error")

	default:
		nblog.Log(ctx).Error().Err(err).Msg("Internal error during login")
		return nil, twirp.InternalError("internal error")
	}

	token, err := auth.IssueToken(ctx, req.Username, int(details.ID.Int), []string{roles[details.Role.Int]})
	if err != nil {
		return nil, err
	}

	nblog.Log(ctx).Debug().Msg("Login successful")
	return &api.LoginResponse{
		Success: true,
		Token:   token,
	}, nil
}

func (neb nebula) CheckToken(ctx context.Context, req *api.NullRequest) (*api.SessionResponse, error) {
	/* if req.Token == "" {
		return nil, twirp.RequiredArgumentError("Token")
	} */

	userInfo, err := auth.GetUser(ctx)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to read user session info")
		return nil, err
	}

	return &api.SessionResponse{
		Valid:    true,
		Username: userInfo.GetUserName(),
	}, nil
}

func (neb nebula) Register(ctx context.Context, req *api.RegisterRequest) (*api.BoolResponse, error) {
	if req.Username == "" {
		return nil, twirp.RequiredArgumentError("Username")
	}
	if req.Password == "" {
		return nil, twirp.RequiredArgumentError("Password")
	}
	if req.Email == "" {
		return nil, twirp.RequiredArgumentError("Email")
	}

	nblog.Log(ctx).Debug().Msgf("Registration received from %s for %s", req.Username, req.Password)
	token, err := nanoid.Generate(nanoid.DefaultAlphabet, 64)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to generate reset token for new user")
		return nil, twirp.InternalError("internal error")
	}

	hashedPass, err := hashPassword(req.Password, neb.Cfg)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to generate password hash for new user")
		return nil, twirp.InternalError("internal error")
	}

	_, err = neb.Q.CreateUser(ctx, queries.CreateUserParams{
		Username:   req.Username,
		Email:      req.Email,
		ResetToken: token,
		Password:   hashedPass,
	})
	if err != nil {
		if db.IsDuplicateKeyError(err) {
			return &api.BoolResponse{Success: false}, nil
		}
		nblog.Log(ctx).Error().Err(err).Msg("Failed to create new user")
		return nil, twirp.InternalError("internal error")
	}

	err = mail.SendRegistrationMail(ctx, neb.Cfg, mail.RegMailParams{
		To:       req.Email,
		Username: req.Username,
		Token:    token,
	})
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to send mail")
		return nil, twirp.InternalError("internal error")
	}

	return &api.BoolResponse{Success: true}, nil
}

func (neb nebula) VerifyAccount(ctx context.Context, req *api.TokenRequest) (*api.BoolResponse, error) {
	if req.Token == "" {
		return nil, twirp.RequiredArgumentError("Token")
	}

	user, err := neb.Q.GetUserByResetToken(ctx, req.Token)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msgf("Failed to look up reset token %s", req.Token)
		return nil, twirp.InternalError("internal error")
	}

	if user.Validated.Bool {
		nblog.Log(ctx).Warn().Msgf("User for token %s has already been validated. Pretending this was succesful. This shouldn't happen!", req.Token)
		return &api.BoolResponse{Success: true}, nil
	}

	_, err = neb.Q.ValidateUser(ctx, user.ID.Int)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msgf("Failed to validate user for token %s", req.Token)
		return &api.BoolResponse{Success: false}, nil
	}

	return &api.BoolResponse{Success: true}, nil
}

func (neb nebula) StartPasswordReset(ctx context.Context, req *api.StartPasswordResetRequest) (*api.BoolResponse, error) {
	if req.Email == "" {
		return nil, twirp.RequiredArgumentError("Email")
	}

	user, userErr := neb.Q.GetUserByEmail(ctx, req.Email)

	// generate a token even if we don't need it to make timing attacks harder; we don't want to tell
	// the user/attacker if the given email exists in our system or not
	token, err := nanoid.Generate(nanoid.DefaultAlphabet, 64)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to generate reset token")
		return nil, twirp.InternalError("internal error")
	}

	if eris.Is(userErr, pgx.ErrNoRows) {
		err := mail.SendResetMail(ctx, neb.Cfg, mail.ResetMailParams{
			To:       req.Email,
			Found:    false,
			Username: "",
			Token:    "",
		})
		if err != nil {
			nblog.Log(ctx).Error().Err(err).Msgf("Failed to send reset mail to %s", req.Email)
			return nil, twirp.InternalError("internal error")
		}

		return &api.BoolResponse{Success: true}, nil
	}

	_, err = neb.Q.SetResetToken(ctx, token, user.ID.Int)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msgf("Failed to update reset token for %s", req.Email)
		return nil, twirp.InternalError("internal error")
	}

	err = mail.SendResetMail(ctx, neb.Cfg, mail.ResetMailParams{
		To:       req.Email,
		Found:    true,
		Username: user.Username.String,
		Token:    token,
	})
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msgf("Failed to send reset mail to %s", req.Email)
		return nil, twirp.InternalError("internal error")
	}

	return &api.BoolResponse{Success: true}, nil
}

func (neb nebula) PreparePasswordReset(ctx context.Context, req *api.TokenRequest) (*api.TokenResponse, error) {
	if req.Token == "" {
		return nil, twirp.RequiredArgumentError("Token")
	}

	user, err := neb.Q.GetUserByResetToken(ctx, req.Token)
	if err != nil {
		if eris.Is(err, pgx.ErrNoRows) {
			return &api.TokenResponse{Token: ""}, nil
		}

		nblog.Log(ctx).Error().Err(err).Msgf("Failed to look up reset token %s", req.Token)
		return nil, twirp.InternalError("internal error")
	}

	token, err := nanoid.Generate(nanoid.DefaultAlphabet, 64)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to generate new reset token")
		return nil, twirp.InternalError("internal error")
	}

	_, err = neb.Q.SetResetToken(ctx, token, user.ID.Int)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msgf("Failed to update reset token for user %d", user.ID.Int)
		return nil, twirp.InternalError("internal error")
	}

	return &api.TokenResponse{Token: token}, nil
}

func (neb nebula) ResetPassword(ctx context.Context, req *api.ResetPasswordRequest) (*api.BoolResponse, error) {
	if req.Token == "" {
		return nil, twirp.RequiredArgumentError("Token")
	}
	if req.Password == "" {
		return nil, twirp.RequiredArgumentError("Password")
	}

	hashedPassword, err := hashPassword(req.Password, neb.Cfg)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to hash password")
		return nil, twirp.InternalError("internal error")
	}

	_, err = neb.Q.SetPasswordByResetToken(ctx, hashedPassword, req.Token)
	if err != nil {
		nblog.Log(ctx).Error().Err(err).Msg("Failed to update password")
		return nil, twirp.InternalError("internal error")
	}

	return &api.BoolResponse{Success: true}, nil
}
