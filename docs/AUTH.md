# Sign-in: PIN, sessions and the school admin

## What it is
A teacher signs in with a **phone number and a 4 to 6 digit PIN**. The server checks the PIN and returns a **signed session token**
(12 hours). The app sends that token with every request. A school admin can reset a forgotten PIN.

## What is protected
**Every API route needs a valid token**, except sign-in, registration, the register template, the competency tree, the curriculum
week and the sample worksheet. A route that names a teacher also needs the token to be **that teacher's**: another teacher's
token on your id gets 403. This is checked for ids in the path, the query string, a form (photo upload, register preview) and a
body (register commit). Printed worksheets and report downloads are fetched with the token and then opened, because a plain
link cannot carry it. Without this a PIN screen would protect nothing, since teacher ids appear in URLs.

## The rules
| Thing | Rule |
| --- | --- |
| PIN | 4 to 6 digits. Not one digit repeated, not a run (1234, 4321), not a very common PIN, not the end of the phone number. Stored only as a PBKDF2 hash (600,000 rounds, salted) |
| Wrong PINs | 5 wrong in a row lock the account for 15 minutes. A school admin can unlock it. A wrong PIN and an unknown phone number give the same answer |
| Session | signed with `SESSION_SECRET`, expires after `SESSION_HOURS` (12). Changing or resetting a PIN ends every session signed before it |
| Roles | `teacher` and `school_admin`. The **first teacher to register a new school code is its admin** and receives a join code. Later teachers must give that code, so knowing a school's name is not enough to join it |
| Admin | can list the school's accounts (the last 4 digits of each phone number, role, number of children, locked or not), reset a PIN, unlock, and make a new join code. **Never sees a child's data**, and cannot touch another school |
| Reset | the admin gets a **temporary 6-digit PIN, shown once**. The teacher can use it only to choose a new PIN: every other route answers 403 until they do |
| Forgotten admin PIN | an admin cannot reset their own. The operator runs `scripts/auth_admin.py set-pin --phone ... --pin ... --must-change` |
| Audit | `auth_events` records registered, login_ok, login_failed, locked, unlocked, pin_changed, pin_reset_by_admin, and every class-report export (the report with names) |

## Settings (environment)
| Variable | Meaning |
| --- | --- |
| `SESSION_SECRET` | **required** unless `DEBUG=true`. A long random string. Changing it signs everyone out |
| `SESSION_HOURS` | length of a sign-in (default 12) |
| `AUTH_MODE` | `enforce` (default, the only value for real use). `off` exists so automated tests of other features can skip sign-in; the server never starts in this mode by default |
| `PIN_HASH_ITERATIONS` | PBKDF2 cost (default 600000); stored with each hash, so it can be raised later |
| `VITE_DEMO_HINT` | the app shows the published demo accounts on the login screen unless this is `false`. Set it to `false` for a real school |

## Demo and test accounts
`is_demo` accounts show a banner (fictional data only). `pin_fixed` accounts are **shared**, so their PIN cannot be changed or
reset: otherwise one tester could lock out the others. One "Change PIN" account (पिन बदलना, the practice account) can be changed, reset and locked freely.
See `docs/DEMO_ACCESS.md`.

## Upgrading an existing database
```
psql -U postgres -d ankur_saathi -f db/schema/09_auth.sql
python scripts/auth_admin.py demo-setup --env-file backend/.env
```
Accounts that exist but have **no PIN cannot sign in** and are told to ask their admin. Set one with `auth_admin.py set-pin`.

## Not done, and worth knowing
- **HTTPS is required in any real deployment.** A PIN and a token sent over plain HTTP can be read on the network.
- The phone number is an **identifier, not a secret**: the app sends `hash_` plus the number, which is not a real hash. The PIN is the secret.
- The token is kept in the browser's local storage, like most single-page apps: a script injected into the page could read it.
  The app does not render untrusted HTML, but this is the usual trade-off against an HttpOnly cookie.
- There is **no limit per network address**, only per account, so a determined guesser can try many different accounts.
  Put a rate limit in front of `/api/auth/login` when hosting.
- No one-time codes by SMS yet (the plan is to add them later); no screen to read the audit trail; registration of a new
  school is open to anyone, which is a prototype convenience.
