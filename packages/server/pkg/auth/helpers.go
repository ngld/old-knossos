package auth

import (
	"context"
	"fmt"
	"net/http"

	gojwt "github.com/dgrijalva/jwt-go/v4"
	"github.com/rotisserie/eris"
	guardian "github.com/shaj13/go-guardian/v2/auth"
	"github.com/shaj13/go-guardian/v2/auth/strategies/jwt"
	"github.com/shaj13/libcache"
	"github.com/twitchtv/twirp"
	"github.com/zpatrick/rbac"

	// Provides libcache.LRU
	_ "github.com/shaj13/libcache/lru"
)

var (
	// ErrMissingParameters is returned if some required fields on the input message are missing / unset
	ErrMissingParameters = eris.New("some parameters are missing")

	// ErrDbIssue is returned if the request could not be processed due to DB issues
	ErrDbIssue = eris.New("a DB query failed")

	// ErrAuthCtxMissing is returned if the request didn't contain an authContext
	ErrAuthCtxMissing = eris.New("auth context missing")
)

type authPtr struct{}

// AuthHandler abstracts authentication *and* authorization over HTTP and possibly other transports
type authContext struct {
	request    *http.Request
	auth       *guardian.Strategy
	jwtSecrets *jwt.StaticSecret
	user       guardian.Info
	role       rbac.Role
}

// MakeAuthMiddleware constructs the necessary middleware required for our Auth* API
func MakeAuthMiddleware(next http.Handler) http.Handler {
	cache := libcache.LRU.New(0)
	secrets := jwt.StaticSecret{
		ID:     "test",
		Method: gojwt.SigningMethodHS256,
		Secret: []byte("TODO"),
	}
	auth := jwt.New(cache, secrets)

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		ctx := r.Context()
		ctx = context.WithValue(ctx, authPtr{}, &authContext{request: r, auth: &auth, jwtSecrets: &secrets})

		r = r.WithContext(ctx)
		next.ServeHTTP(w, r)
	})
}

func getAuthContext(ctx context.Context) (*authContext, error) {
	authCtxPtr := ctx.Value(authPtr{})
	if authCtxPtr == nil {
		return nil, ErrAuthCtxMissing
	}

	return authCtxPtr.(*authContext), nil
}

// IssueToken generates a new session token with the associated user
func IssueToken(ctx context.Context, username string, uid int, roles []string) (string, error) {
	authCtx, err := getAuthContext(ctx)
	if err != nil {
		return "", err
	}

	user := guardian.NewUserInfo(username, fmt.Sprint(uid), roles, nil)
	return jwt.IssueAccessToken(user, *authCtx.jwtSecrets)
}

// GetUser returns the current user info
func GetUser(ctx context.Context) (guardian.Info, error) {
	authCtx, err := getAuthContext(ctx)
	if err != nil {
		return nil, err
	}

	if authCtx.user == nil {
		authCtx.user, err = (*authCtx.auth).Authenticate(ctx, authCtx.request)
		if err != nil {
			twerr := twirp.NewError(twirp.Unauthenticated, "token missing or invalid")
			return nil, twirp.WrapError(twerr, err)
		}
	}
	return authCtx.user, nil
}

// GetRole checks authentication if necessary and returns the user's role
func GetRole(ctx context.Context) (*rbac.Role, error) {
	authCtx, err := getAuthContext(ctx)
	if err != nil {
		return nil, err
	}

	if authCtx.role.RoleID == "" {
		user, err := GetUser(ctx)
		if err != nil {
			return nil, err
		}

		authCtx.role, err = getRbacRole(user.GetGroups()[0])
		if err != nil {
			return nil, err
		}
	}

	return &authCtx.role, nil
}

// CheckPermission verifies that the currently authenticated user has the given permission
func CheckPermission(ctx context.Context, perm Permission, bag Bag) error {
	role, err := GetRole(ctx)
	if err != nil {
		return err
	}

	encBag, err := MarshalBag(bag)
	if err != nil {
		return err
	}

	allowed, err := role.Can(string(perm), encBag)
	if err != nil {
		return err
	}

	if !allowed {
		return twirp.NewError(twirp.PermissionDenied, "permission denied")
	}

	return nil
}
