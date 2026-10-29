# Privacy: children's names

A teacher may enter each child's name in the class register. The name is **teacher-only**: it is shown on her own screens
and in her own class report, and it is **never sent to the AI**. This page says exactly what that means, how it is
enforced, and what is NOT yet done.

## Where each kind of data goes
| Data | Stored | Shown to the teacher | Sent to the AI | In the officer (MLO) report |
| --- | --- | --- | --- | --- |
| Class number (101, 305, or the roll) | yes | yes | **yes** (the AI needs it to form groups and match a sheet to a child) | yes |
| Name | yes, in its own table (`child_names`) | yes | **no** | **no** |
| Worksheet photo | not kept after analysis | n/a | **yes** (that is what is analysed) | no |
| Scores, patterns, levels | yes | yes | scores are computed from the AI's reading | levels only |

## How "never sent to the AI" is enforced
1. **Names live in their own table**, read by one small module (`names_service.py`). The code that builds a request to the AI
   (plan generation, the prompts, the worksheet renderer) does not import it and cannot reach the table.
2. **`backend/tests/test_names_static_guard.py`** fails if any of those modules mentions names, if the worksheet template gets a
   name field, if the officer report refers to names, or if any other module reads the names table. (Checked by deliberately
   breaking each rule: all are caught.)
3. **`backend/tests/test_names_never_reach_ai.py`** gives every child a canary name, sends a photo through the real analysis
   code with a stand-in for the AI, and checks the real outgoing request for the canary. Plan generation was checked the
   same way against a real plan: 1 request, about 16,000 characters, class numbers present, no name or surname.
4. **The officer report cannot carry names.** The teacher's class report (with names) is a separate download.

## Audio
The app **records no audio** and never asks the browser for the microphone (`pwa/tests/no_audio.test.mjs` checks the code and the screens). Reading aloud is timed by the teacher, who types the result. If voice assessment is added for the periodic assessments (`docs/ROADMAP.md`, section 6), it will need the school's consent on record and audio that is scored in memory and not kept, as photos are; none of that is built.

## Consent
A school is made by the department (or, today, the operator), not by its teachers. At the **first sign-in of its leader** (the head teacher), she confirms on one screen that the children's parents or guardians have been told that the children's classwork will be read in the app and have given their permission, that photos are read by an AI and are not kept, and that children's names are never sent to the AI. The confirmation is kept with its exact wording, the version of that wording, the date and who gave it (the table `school_consents`). The leader sees it in her Profile; the leader of a school that has none can confirm there too. **Teachers are never asked**, because the school confirmed once, through its leader. The demonstration school carries the statement that every child in it is fictional.

**What this is not.** It is the school's confirmation, **not a record of consent from each parent**. The app holds no parent's name, signature or date of permission, and it cannot check that what the school says is true. Recording each parent's consent, and the lawful basis under India's Digital Personal Data Protection Act, 2023, remains to be agreed with the school and the state (see the list at the end of this document).

## Names the AI might read off a photo
The AI is told never to use names. But a child may write their name in a notebook, and a **photo goes to the AI** whatever
we do in the database. So:
- the printed worksheet has only a roll / class number box, never a name box;
- the photo screen tells the teacher to keep names out of the photo;
- after the AI answers, any class member's name (full name or any part of it) found in its reply is replaced with
  "[नाम हटाया]" **before anything is stored**. This is a safety net, not a guarantee: it only knows the names in the register,
  and it never removes a name from the photo itself.

## Before real children's names are used (not done yet)
1. **Login.** Done: an employee code and a password with lockout, signed sessions on every route and a school leader who can reset a password (`docs/AUTH.md`). What
   remains is HTTPS and a rate limit per network address when hosting.
2. **HTTPS everywhere, encryption at rest, and backups** that are handled as personal data.
3. **A lawful basis and consent** for processing children's data, agreed with the school and the state. India's Digital
   Personal Data Protection Act, 2023 has special provisions for children's data: confirm the exact obligations for your
   deployment with the school or state's data-protection contact. This page is not legal advice.
4. **What the AI provider retains** is set by its API terms for your account. Check them, and ask for a zero-retention option
   if the school requires one. Photos are the only identifying content that reaches it.
5. **Editing and deleting names.** A name can be added or corrected by uploading a register again. There is no screen yet to
   delete one name or one child; deleting a child removes their name with it (`ON DELETE CASCADE`).
6. **Access logging:** sign-in events and every export of a class report (the one with names) are recorded in `auth_events`; there is no screen to read them yet.

## Teachers' employee codes and passwords
- **A teacher's employee code is her sign-in.** It is an official identifier (six letters or digits, such as MPT101), stored as given in capitals. **No phone number is stored for an account made with an employee code.** (Accounts made before employee codes were named `hash_` plus a phone number, and the column is still called `phone_hash`: it never held a real hash. The demonstration accounts have been renamed, and the nightly job renames them in the cloud.)
- **The password is hashed properly:** PBKDF2-SHA256 with a random salt; the iteration count is stored with each hash so it can be raised later (`docs/AUTH.md`). A wrong password and an unknown code get the same answer, so the sign-in does not reveal which codes exist.
- **Who sees a code:** the school leader's list shows the codes of her own school's accounts and nothing else; a code is never sent to the AI, never put in a log line by the app, and never shown to another school.
- **Not done yet:** a one-time code by SMS or WhatsApp, or the state's own sign-in, instead of a fixed password; and linking the codes to the department's employee records.

## Demo and test data
The repository contains **fictional first names only** (`db/seeds/classroom/02_child_names.sql`, and the list in
`scripts/create_test_teachers.py`). A real class's names are entered by the teacher in her own app and never belong in this
repository or in the submission.
