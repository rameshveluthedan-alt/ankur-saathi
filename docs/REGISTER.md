# Class register: enrolling a class

Nothing else in the app can create a teacher or a child, so every class starts here.

## A new teacher
On the login screen choose **New teacher? Register**: phone number, school code, the grades taught (Balvatika, Grade 1, 2, 3) and a **PIN**.
A new school code creates the school and makes this teacher its **admin** (who receives a join code). To join a school that already
exists, give its join code (`docs/AUTH.md`).

## Uploading the register
Plan screen > **Class register**. Download the template, fill it in, choose the file, read the preview, confirm.

| Column | Meaning |
| --- | --- |
| `grade` | 0 (Balvatika), 1, 2 or 3. Also accepted: `grade_2`, `Grade 2`, `कक्षा 2`, `२`, `II` |
| `roll_number` | the school's own roll, 1 to 99 |
| `name` | optional (also `नाम`, `student name`). Kept private: shown only to the teacher, **never sent to the AI**, never in the officer report. Up to 80 characters. See `docs/PRIVACY.md` |
| `numeracy_level`, `literacy_level` | optional: `beginner`, `progressor`, `proficient` (or शुरुआती, प्रगतिशील, दक्ष). Empty means progressor, until a baseline or the daily evidence says otherwise |

- **Names are optional and private.** The app identifies children by number everywhere it talks to the AI. A name is stored apart, shown on the teacher's own screens, and appears only in her class report. Uploading a register again with names adds or corrects them for children already enrolled.
- CSV (commas, semicolons or tabs; UTF-8 or Excel's encodings) works everywhere. Excel (.xlsx) works when the server has
  `openpyxl` (`pip install openpyxl`). Lines starting with `#` are ignored. Hindi column headers and Devanagari digits are accepted.
- **Nothing is written until you confirm.** The preview shows how many children will be added, which are already
  enrolled (skipped), and every problem against its own line (not added). Uploading the same file twice adds no one twice.

## Class numbers in a multi-grade class
Everything in the app looks a child up by one number in the class. If the school's rolls are unique across the whole
class (1 to 30 straight through) they are used as they are. If they repeat across grades (roll 5 of Grade 1 and roll 5 of
Grade 3), each child gets a **class number that carries the grade**: grade x 100 + roll (Grade 3, roll 5 = **305**;
Balvatika keeps its roll). Children write that one number on worksheets, which then say "Class No." with the hint
"जैसे 305 = कक्षा 3, रोल 5". The Review screen shows the grade and school roll next to it ("G3·5").

## Test teachers (for testers who must not share one account)
```
python scripts/create_test_teachers.py create --count 5 --env-file backend/.env     # 9000000101 ... 9000000105
python scripts/create_test_teachers.py list   --env-file backend/.env
python scripts/create_test_teachers.py remove --env-file backend/.env               # only these test teachers
```
Each has their own multi-grade class (class numbers 101-110, 201-208, 301-306) enrolled through the same code as the
screens, with fictional first names (`--no-names` to skip). The demo teacher (9876543210) is not touched.

## Database
`db/schema/07_register.sql` adds `children.school_roll` and an upload log; `db/schema/08_child_names.sql` adds the names table.
On an existing database run both once, then restart the backend. Until 07 is loaded the register says so (503); until 08 is
loaded children are still enrolled and the preview says the names cannot be saved yet. The rest of the app keeps working.

## Not built
A school-admin role that uploads registers for several teachers, deactivating children who left, and moving a child
between grades. Each needs its own permissions and test credentials.
