# Roadmap: roles, onboarding and integration (a design sketch: only the school leader's part is built)

**Where the build is today.** Two roles exist: *teacher* and *school leader* (the head teacher, who teaches too; stored as `school_admin`). Everyone signs in with an employee code and a password; nobody registers themselves. The leader can list the school's accounts, reset a password, unlock an account and confirm the school's consent statement at her first sign-in. Each teacher enrols her own class by uploading a register. The operator makes the accounts. There is nothing above the school (`docs/STATUS.md`, `docs/AUTH.md`).

**Why this needs design, not patching.** A state rollout is not a set of independent schools. Who enrols a school, who may see which child's data, and who answers to whom are questions about the whole hierarchy. Adding admin screens one at a time would bake in answers we have not chosen. The sketch below mirrors how school education is administered, and keeps one rule: **the closer to the child, the more detail; the higher up, the more aggregate.**

## 1. Who does what (a starting point for discussion)
| Role | Does | Sees | Does not see or do |
|---|---|---|---|
| **State admin** (super admin) | Loads the state's school list (district, block, school code) in bulk; creates district admins; sets state-wide settings (the weekly curriculum plan, language, AI limits) | State totals: schools onboarded, teachers active, plans generated, level mix | Any child's name, photo or answers |
| **District admin** | Oversees the schools of one district; creates block coordinators; invites school admins | The district's aggregates, schools that are inactive, and children flagged "consider re-assessing" as counts | Names, photos |
| **Block / cluster coordinator** (the academic support role, often called BRC or CRC) | Supports the schools of one block or cluster; reads how each school is doing | Per-school aggregates and trends; read-only | Names, photos; no changes to a school |
| **School leader** (head teacher, who teaches too) | Claims the school; invites and approves teachers; assigns teachers to grades and classes; enrols or syncs the class registers; resets passwords; confirms the school's consent | Her school's reports (level mix per class, plan use, flags) and, if decided (below), the names of her own school's children | Other schools; photos of children's work |
| **Teacher** | Plans, teaches, reviews, records decisions for her own classes | Her own children, by name, and their evidence | Other teachers' classes (unless a school admin assigns her to them) |
| **Observer** (evaluator, auditor) | Read-only access to a defined scope | Aggregates for that scope | Everything else |

## 2. How a state rollout would start (top down)
1. The state admin uploads the school list (the school code from the national school database, name, block, district).
2. Each school and its leader (by employee code) come from the department's lists; the leader signs in with a temporary password, chooses her own and confirms the school's consent statement.
3. The school leader adds teachers (one by one or from a CSV file: the next step, not built; today the operator makes accounts) and assigns them to grades.
4. Class registers are uploaded by the teacher or by the school admin, or synced from the state's student register where one exists.
5. A baseline places the children; daily use starts.

## 3. Data rules that follow from "closer to the child, more detail"
- **Names and photos stay at the teacher (and, if decided, the school).** District, state and block roles see counts, percentages and trends, never a name. This is data minimisation under the DPDP Act, and it removes the strongest objection to an officer dashboard.
- **Every look at sensitive data is recorded** (`auth_events` already records sign-ins and class report exports; it needs a screen).
- **Scope is part of every permission:** a role is always "this role *for this part of the hierarchy*", checked in one place (today `require_auth`), never per screen.
- **Consent is recorded where it is given:** at the school, with a name and a date.

## 4. Open design questions (to settle with the state before building)
1. May the **school admin see children's names**? (The head teacher usually knows them; the teacher is who the data was entrusted to.)
2. Who creates a teacher's account: the school leader alone, or with a block officer's **approval**?
3. Can **one person hold several roles** or schools (a teacher who also covers a second school)?
4. Which **national and state systems** can supply the school list and the student register, and how do we match them without storing more than needed?
5. How do people **sign in** at scale: an employee code with a password (today), a one-time code by SMS or WhatsApp, or the state's own identity system?

## 5. What changes in the build
- A hierarchy table (state, district, block, cluster, school) and a **membership table** (person, unit, role) replace the single `teachers.role` column.
- One permission function answers "may this person do this to that unit?"; aggregates are computed in the database, so upper roles never receive child-level rows.
- Bulk school import, invitations and approvals, an access-log screen, and a **per-role test matrix** in the style of `tests/test_auth_flow.py` (every role against every scope, including the refusals).

## 6. Assessment modes: daily and periodic
**Daily review (built): no audio.** A teacher records what she saw in one of three ways, and the screen offers only the one that fits the skill: a photo of the worksheet (the AI reads it), a quick tap of *achieved / partly / not yet* for each child (observation), or the **reading-aloud** form, where she listens to one child for a minute and enters the correct words and the errors. Nothing is recorded: in a class where several groups are at work at once, a recording is too noisy to be clear, so the daily review is by observation.

**Periodic assessments (planned): both modes.** Every few weeks a child is assessed on purpose, in a quiet moment and one to one. There the teacher should be able to choose **observation** (as above) or **voice**: a short recording of the child reading, scored by speech recognition for Hindi, which the teacher confirms or corrects. Voice needs decisions first: parental consent recorded at the school (section 3); audio scored in memory and **not stored**, as photos are today; recognition that is good enough for young children's Hindi (to be measured on real recordings before it is offered); and a recording that still works on a weak connection.

## 7. Phases
| Phase | What | Rough size |
|---|---|---|
| 1 | **School admin console:** a read-only school overview (class sizes, level mix, last active), a school report download, admin creates a teacher account | days |
| 2 | **The hierarchy:** state and district roles, bulk school onboarding, aggregate dashboards | one to two weeks |
| 3 | **Integration and voice:** the national school list, a one-time-code sign-in, importing state assessment results to place children (`docs/LEVELS.md`), voice assessment for the periodic rounds | depends on the state's systems |
| 4 | **Officer views and the second state:** trends, the block coordinator's mentoring view, another state's curriculum plan | follows 2 and 3 |

*Other roadmap items* (periodic assessment rounds with history, baseline screens, WhatsApp notifications, voice recording for the periodic assessments (section 6), second-language literacy, PDF export) are listed in `docs/STATUS.md`.

## 7. Next, designed on 27 Oct and not built: the school leader's screens and the officers' reports
Decided with the team after the first tests (the head teacher is the school's administrator; she also teaches and often coaches her teachers):
- **Adding teachers:** a form (employee code, grades) that makes a temporary password, shown once; and a CSV upload with a preview before it is confirmed, the same way the class register is uploaded. There is no bulk upload of schools: a school and its leader are loaded by the department, so each leader looks after one school.
- **Reports, for the leader and for a block or cluster officer (BAC or CRC):** counts only, never a name: teachers active this week, plans made, how many groups were re-taught and how many moved on, children by level, the skills taught most. The leader sees her own school; an officer sees the schools of her block or cluster.
- **The officer's role** is read-only and is stored with the account and its scope (a list of schools), never read from the letters of her employee code.
- **Demonstration data:** about three fictional schools with a few teachers each, so the reports are not empty.
