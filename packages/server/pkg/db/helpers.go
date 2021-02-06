package db

import (
	"strings"

	"github.com/jackc/pgconn"
)

// IsDuplicateKeyError returns true if the passed error indicates that the last INSERT failed because
// a unique constraint was violated
func IsDuplicateKeyError(err error) bool {
	pgErr, ok := err.(*pgconn.PgError)
	if ok {
		return pgErr.Code == "23505"
	} else {
		return strings.Contains(err.Error(), "(SQLSTATE 23505)")
	}
}
