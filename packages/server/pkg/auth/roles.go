package auth

import (
	"github.com/ngld/knossos/packages/server/pkg/db"
	"github.com/ngld/knossos/packages/server/pkg/db/queries"
	"github.com/rotisserie/eris"
	"github.com/zpatrick/rbac"
)

// ErrInvalidRole is returned if the current user has an invalid role
var ErrInvalidRole = eris.New("invalid user role")
var roles map[string]rbac.Role

type Permission string

const (
	// Mods [takes ModBag]
	PermViewMod   Permission = "ViewMod"
	PermCreateMod Permission = "CreateMod"
	PermEditMod   Permission = "EditMod"
	PermDeleteMod Permission = "DeleteMod"

	// Special perms [takes ModBag]
	PermEditModTeam  Permission = "EditModTeam"
	PermCreateEngine Permission = "CreateEngine"

	// Releases [takes ModBag]
	PermViewRelease   Permission = "ViewRelease"
	PermCreateRelease Permission = "CreateRelease"
	PermEditRelease   Permission = "EditRelease"
	PermDeleteRelease Permission = "DeleteRelease"

	// Users [takes UserBag]
	// Note: CreateUser does *not* apply to the normal registration process
	PermCreateUser Permission = "CreateUser"
	PermEditUser   Permission = "EditUser"
	PermDeleteUser Permission = "DeleteUser"
)

// perm is a helper that makes the permissions list below a bit nicer to read
func perm(permission Permission, matcher rbac.Matcher) rbac.Permission {
	return rbac.NewPermission(rbac.StringMatch(string(permission)), matcher)
}

// Init prepares static objects used throughout the lifecycle
func Init(q *queries.DBQuerier) {
	roles = map[string]rbac.Role{
		"guest": {
			RoleID: "guest",
			Permissions: []rbac.Permission{
				perm(PermViewMod, publicMod(q)),
				perm(PermViewRelease, publicRelease(q)),
			},
		},
		"member": {
			RoleID: "member",
			Permissions: []rbac.Permission{
				// everyone create new mods
				perm(PermCreateMod, rbac.Anything),

				// members can view public mods and private mods if they're part of the team
				perm(PermViewMod, publicMod(q)),
				perm(PermViewMod, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader, db.ModRoleTester})),

				// members can edit mods if they have the necessary role (owner or uploader)
				perm(PermEditMod, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader})),

				// only owners can edit team members or delete the mod
				perm(PermEditModTeam, modRole(q, []db.ModRole{db.ModRoleOwner})),
				perm(PermDeleteMod, modRole(q, []db.ModRole{db.ModRoleOwner})),

				// members can view public releases and private releases if they're part of the team
				perm(PermViewRelease, publicRelease(q)),
				perm(PermViewRelease, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader, db.ModRoleTester})),

				// members can create, edit and delete(!) releases if they have the necessary role (owner or uploader)
				perm(PermCreateRelease, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader})),
				perm(PermEditRelease, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader})),
				perm(PermDeleteRelease, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader})),

				// members can only edit themselves
				perm(PermEditUser, userSelf(q)),
			},
		},
		"moderator": {
			RoleID: "moderator",
			Permissions: []rbac.Permission{
				perm(PermCreateMod, rbac.Anything),

				// mods can also create engines
				perm(PermCreateEngine, rbac.Anything),

				// mods can view, edit and delete all mods and releases
				perm(PermViewMod, rbac.Anything),
				perm(PermEditMod, rbac.Anything),
				perm(PermDeleteMod, rbac.Anything),

				perm(PermViewRelease, rbac.Anything),
				perm(PermEditRelease, rbac.Anything),
				perm(PermDeleteRelease, rbac.Anything),

				// mods can also edit mod teams
				perm(PermEditModTeam, rbac.Anything),

				// mods can only create new releases for their own mods
				perm(PermCreateRelease, modRole(q, []db.ModRole{db.ModRoleOwner, db.ModRoleUploader})),

				// mods can edit and delete users
				perm(PermEditUser, rbac.Anything),
				perm(PermDeleteUser, rbac.Anything),
			},
		},
		"admin": {
			RoleID: "admin",
			Permissions: []rbac.Permission{
				// admins can do anything
				rbac.NewGlobPermission("*", "*"),
			},
		},
	}
}

// getRbacRole returns the matching rbac.Role for the given role ID
func getRbacRole(roleID string) (rbac.Role, error) {
	role, ok := roles[roleID]
	if !ok {
		return rbac.Role{}, eris.Wrapf(ErrInvalidRole, ": %s", roleID)
	}

	return role, nil
}
