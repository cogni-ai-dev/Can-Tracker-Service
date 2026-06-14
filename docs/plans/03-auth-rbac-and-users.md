# Plan 03: Auth, RBAC, And Users

## Goal

Implement email/password login, secure sessions, role-based access control, user management, and RM visibility rules.

## Context

The generated HTML has a hardcoded current user. The backend must track who updated records and must restrict visibility and actions by role.

Selected v1 access model: one distributor firm with users assigned one of four roles: `admin`, `ops`, `rm`, `management`.

## In Scope

- User model.
- Password hashing.
- Login, logout, and current-user endpoints.
- Session handling with secure HttpOnly cookies.
- Role guards and endpoint dependency helpers.
- RM assignment and visibility rules.
- User management APIs for Admin.
- Auth and authorization tests.

## Out Of Scope

- Multi-tenant SaaS isolation.
- SSO or OAuth.
- Password reset email delivery.
- Two-factor authentication.
- Fine-grained custom permissions.

## Design

### User Fields

`users` table:

- `id`: UUID.
- `name`: required display name.
- `email`: required unique lowercase email.
- `password_hash`: required for email/password users.
- `role`: one of `admin`, `ops`, `rm`, `management`.
- `is_active`: boolean.
- `last_login_at`: nullable timestamp.
- `created_at`, `updated_at`, `deleted_at`.

### Roles

`admin`:

- Full system access.
- Create, update, deactivate users.
- View sensitive fields when explicitly requested.
- Manage all families, members, imports, reports, and audit logs.

`ops`:

- Create and update families and members.
- Run imports.
- Export reports.
- View masked sensitive fields by default.
- View full sensitive fields only if explicitly granted by a future setting. Default v1 is masked.

`rm`:

- View assigned families and members.
- Update operational fields for assigned families if allowed by v1 policy.
- Export reports only for assigned families.
- Cannot manage users.

`management`:

- Read dashboards and reports.
- View masked sensitive fields.
- Cannot create, update, delete, or import records.

### Session Model

Use server-side sessions or signed session tokens stored in HttpOnly cookies. For v1, prefer server-side sessions if the implementation needs revocation, otherwise signed cookies are acceptable if logout invalidation is handled.

Cookie requirements:

- HttpOnly.
- SameSite `lax`.
- Secure in production.
- Configurable name from `SESSION_COOKIE_NAME`.

### Endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}` for soft deactivate or soft delete.
- `GET /api/v1/rms` for RM filter dropdowns.

### RM Visibility

Families are assigned through `families.primary_rm_id`.

Rules:

- Admin, Ops, and Management can read all active families.
- RM can read only families where `primary_rm_id = current_user.id`.
- RM dashboard counters include only assigned families.
- RM task lists include only assigned families.
- RM report exports include only assigned families.
- If a family is reassigned, the old RM loses access immediately.

## Implementation Steps

1. Add `UserRole` enum.
2. Add `users` migration.
3. Add password hashing with Argon2id or bcrypt.
4. Add login, logout, and current-user routes.
5. Add route dependencies: `require_user`, `require_roles`, `can_view_family`, `can_update_family`.
6. Add Admin user management routes.
7. Add `GET /api/v1/rms` for active RM users.
8. Apply role guards to any existing health-safe routes only where needed.
9. Seed a local development admin through a command or migration-safe bootstrap script.
10. Add authorization tests before exposing business endpoints.

## Subagent Usage

- Use `cavecrew-investigator` to locate all route modules before applying role guards once business endpoints exist.
- Use the main thread for session and authorization design because mistakes affect all endpoints.
- Use `cavecrew-reviewer` to audit for missing role checks and inactive-user bypasses.
- Use `cavecrew-builder` only for small follow-up edits to one route file or one test file.

## Test Plan

- Login succeeds with valid active user.
- Login fails with wrong password.
- Login fails for inactive user.
- Logout clears session.
- `GET /auth/me` returns the current user without password hash.
- Admin can create, update, list, and deactivate users.
- Ops, RM, and Management cannot manage users.
- RM cannot access families assigned to another RM.
- Management can read but cannot write.
- All protected endpoints reject anonymous requests.

## Acceptance Criteria

- Every protected route requires an authenticated active user.
- Every role rule is covered by at least one test.
- Password hashes are never returned in API responses.
- User updates are auditable once Plan 04 is implemented.
- RM scoping behavior is reusable by dashboard, tasks, reports, and CRUD endpoints.

## Risks & Mitigations

- Risk: role checks are inconsistently applied. Mitigation: centralize dependencies and test each route group.
- Risk: sessions are hard to revoke. Mitigation: prefer server-side sessions if revocation is required.
- Risk: seed admin credentials leak. Mitigation: require environment-provided bootstrap password and force change later if needed.

## Dependencies

- [01-domain-model-and-business-rules.md](01-domain-model-and-business-rules.md)
- [02-backend-foundation.md](02-backend-foundation.md)

