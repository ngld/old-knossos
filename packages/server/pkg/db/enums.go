package db

// UserRole models the valid values for users.role
type UserRole int16

const (
	UserRoleGuest UserRole = iota + 1
	UserRoleMember
	UserRoleModeration
	UserRoleAdmin
)

// ModRole models the valid values for mod_team_members.role
type ModRole int16

const (
	ModRoleOwner ModRole = iota + 1
	ModRoleUploader
	ModRoleTester
)

// ModType models the valid values for mods.type
type ModType int16

const (
	TypeMod ModType = iota + 1
	TypeTotalConversion
	TypeEngine
	TypeTool
	TypeExtension
)

type EngineStability int16

const (
	EngineUnknown EngineStability = 0
	EngineStable  EngineStability = iota + 1
	EngineRC
	EngineNightly
)

type PackageType int16

const (
	PackageRequired PackageType = iota + 1
	PackageRecommended
	PackageOptional
)
