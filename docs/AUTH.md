# Sign-in: employee codes, passwords, sessions and the school leader

## What it is
Everyone signs in with a **6-character employee code** (letters and digits; the demo ones are three letters and three digits, such as MPT101) and a **password**. The server checks the password and returns a **signed session token**
(`SESSION_HOURS`: 12 by default, 168, which is 7 days, in the cloud settings so that a teacher on her own phone rarely types it). The app sends that token with every request. **Nobody registers themselves:** the **school leader** (the head teacher, who teaches too)
looks after her school's accounts and can reset a forgotten password. Today the operator makes the accounts; adding teachers from the leader's own screen is the next step (`docs/ROADMAP.md`).

## What is protected
**Every API route needs a valid token**, except sign-in, the register template, the competency tree, the curriculum
week and the sample worksheet. A route that names a teacher also needs the token to be **that teacher's**: another teacher's
token on your id gets 403. This is checked for ids in the path, the query string, a form (photo upload, register preview) and a
body (register commit). Printed worksheets and report downloads are fetched with the token and then opened, because a plain
link cannot carry it. Without this a password screen would protect nothing, since teacher ids appear in URLs.

## The rules
| Thing | Rule |
| --- | --- |
| Employee code | six letters or digits, stored in capitals and typed in any case. It is an identifier, **not a secret**. The role is never read from its letters: it is stored with the account (a teacher's code may start with MPA, a leader's with MPT) |
| Password | 6 to 12 letters or digits (a 6-digit number is fine). Not one character repeated, not a run of digits (123456), not a very common password, not the employee code. Stored only as a PBKDF2 hash (600,000 rounds, salted). The shared demo accounts keep their published 4-digit passwords: nobody can SET a 4-digit one |
| Wrong passwords | 5 wrong in a row lock the account for 15 minutes. The school leader can unlock it. A wrong password and an unknown code give the same answer: "The employee code or password is not right" |
| Session | signed with `SESSION_SECRET`, expires after `SESSION_HOURS`. Changing or resetting a password ends every session signed before it |
| Roles | `teacher` and `school_admin`, shown to people as **school leader** (the head teacher). Block and cluster officers, who would see reports, are designed in `docs/ROADMAP.md` and not built |
| School leader | can list the school's accounts (each by employee code, role, number of children, locked or not), reset a password, unlock, and confirm the school's consent statement. **Never sees a child's data**, and cannot touch another school |
| Reset and first sign-in | the leader gets a **temporary 6-digit password, shown once**. The teacher can use it only to choose her own: every other route answers 403 until she does. An account made with a temporary password has the same first screen |
| The school's consent | at the first sign-in of a school with no confirmation on record, the leader sees one screen and confirms the statement (`docs/PRIVACY.md`, "Consent"). Teachers are never asked. A demonstration school carries its own statement |
| Forgotten leader password | she cannot reset her own. The operator runs `scripts/auth_admin.py set-pin --code ... --pin ... --must-change` |
| Registration | **closed.** The route exists only for a practice database (`SELF_REGISTRATION=true`); it answers 403, `registration_closed`, otherwise. There is no join code |
| Audit | `auth_events` records registered, login_ok, login_failed, locked, unlocked, pin_changed, pin_reset_by_admin, consent_recorded, and every class-report export (the report with names) |

## Settings (environment)
| Variable | Meaning |
| --- | --- |
| `SESSION_SECRET` | **required** unless `DEBUG=true`. A long random string. Changing it signs everyone out |
| `SESSION_HOURS` | length of a sign-in (default 12; 168 in `deploy/cloudrun-env.yaml`) |
| `SELF_REGISTRATION` | `false` by default. `true` only on a practice database, where a person may register a school and teachers through the API |
| `AUTH_MODE` | `enforce` (default, the only value for real use). `off` exists so automated tests of other features can skip sign-in; the server never starts in this mode by default |
| `PIN_HASH_ITERATIONS` | PBKDF2 cost (default 600000); stored with each hash, so it can be raised later |
| `VITE_DEMO_HINT` | the app shows the published demo accounts on the login screen unless this is `false`. Set it to `false` for a real school |

## Demo and test accounts
`is_demo` accounts show a banner (fictional data only). `pin_fixed` accounts are **shared**, so their password cannot be changed or
reset: otherwise one tester could lock out the others. One practice account (MPT199) can be changed, reset and locked freely.
There is one demo school with one leader (MPA101); the test teachers MPT102 and up teach in it. See `docs/DEMO_ACCESS.md`.
A demo code looks like a real employee code, so **every script that touches a demo account acts only inside the demo school**: a real teacher with the same code in another school is never renamed, moved, reset or deleted (`backend/tests/test_test_teachers.py`).

## Upgrading an existing database
```
psql -U postgres -d ankur_saathi -f db/schema/09_auth.sql
python scripts/migrate_to_employee_codes.py --env-file backend/.env
python scripts/auth_admin.py demo-setup --env-file backend/.env
```
The migration renames the demo accounts that were named by a phone number (9876543210 became MPT101, 9876500000 MPA101, 9000000199 MPT199, 9000000101 and up MPT102 and up), keeps each one's class, children, plans and evidence, moves the
test teachers into the demo school and removes the old test admin and the empty test school. It is safe to repeat, and the nightly job runs it first, so a deploy converts the cloud database by itself.
Accounts that exist but have **no password cannot sign in** and are told to ask their school leader. Set one with `auth_admin.py set-pin`.

## Not done, and worth knowing
- **HTTPS is required in any real deployment.** A password and a token sent over plain HTTP can be read on the network. On Cloud Run the address is HTTPS only (deploy/DEPLOY.md), and the app sends
  `Strict-Transport-Security` and other security headers.
- The employee code is an **identifier, not a secret**; the password is the secret. No phone number is stored for an account made with an employee code.
- The token is kept in the browser's local storage, like most single-page apps: a script injected into the page could read it.
  The app does not render untrusted HTML, but this is the usual trade-off against an HttpOnly cookie.
- The lockout is per account, so on its own it would not stop one address trying many accounts. **A limit per network
  address is built** (`backend/app/rate_limit.py`, switched on by `app/production.py`): by default 20 sign-ins a minute and 10 password changes a minute per address (and 5 registrations an hour, for a practice database), answered with
  HTTP 429 and a `Retry-After` header. The address is the last entry of `X-Forwarded-For`, the one Google's front end added, because a client can write anything at the start. The counts are kept
  in memory per container, so with up to 3 containers the real limit can be up to 3 times higher; that is acceptable for a demo, and a shared store would be needed for more. Change the numbers
  with `RATE_LOGIN_PER_MIN`, `RATE_REGISTER_PER_HOUR`, `RATE_CHANGE_PIN_PER_MIN`.
- No one-time codes by SMS or WhatsApp yet, no sign-in through the state's own identity system, no screen to read the audit trail, and no screen to add teachers (one by one or from a CSV file). The school and its leader are loaded by the department or the operator.
- The request field that carries the password is still called `pin` and the endpoint `change-pin`, from when it was a PIN; the screens say "password" everywhere.
