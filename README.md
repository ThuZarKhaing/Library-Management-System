# Library Management System

A library system written in Python, built around object-oriented programming: classes,
encapsulation, inheritance, polymorphism, composition, lists of objects, JSON persistence,
a Tkinter desktop app, and a Flask web dashboard with role-based access control.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Flask](https://img.shields.io/badge/web-flask-black) ![Tkinter](https://img.shields.io/badge/gui-tkinter-orange) ![Tests](https://img.shields.io/badge/tests-90%20passing-brightgreen) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

| | |
|---|---|
| Add and remove books | ID, title, author, category |
| Register and remove members | Students and teachers |
| Borrow and return books | Availability and limits are checked automatically |
| Two member types | Student = 3 books, Teacher = 10 books (one method, two answers) |
| Three front ends | Console menu, Tkinter desktop app and Flask web dashboard |
| Two user roles | `admin` manages everything, `staff` handles the desk |
| Logins and passwords | Salted PBKDF2-SHA256, never stored in plain text |
| CSRF protection | Every form is signed; unsafe redirects are refused |
| Live search | Filter by title, author or category as you type |
| Persistent storage | JSON files, written after every change |
| Test suite | 90 unit tests plus a 35-check live HTTP check |

## How to run

Requires Python 3.8 or newer. The console and desktop versions need no third-party
packages: `tkinter` ships with Python on Windows and macOS, and on Linux it comes from
the `python3-tk` package. The web dashboard needs Flask.

```bash
git clone https://github.com/ThuZarKhaing/Library-Management-System.git
cd Library-Management-System

python main.py            # console menu, data is saved automatically
python main.py --demo     # scripted tour of every rule, no typing needed
python main.py --gui      # desktop application
```

### Web dashboard

```bash
pip install -r requirements.txt
python main.py --web
```

Then open <http://127.0.0.1:5000>.

Two accounts are created automatically the first time the program runs:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin12345` | Administrator |
| `staff` | `staff12345` | Front desk staff |

> Change these passwords before using the dashboard anywhere other than your own
> machine. `admin` can set new ones from **My account**.

## What each role can do

Permissions live in one table in `services/permissions.py`, and the templates ask it what
to show, so the menu a user sees and the routes they can reach can never disagree.

| | Staff | Admin |
|---|:--:|:--:|
| See the dashboard | yes | yes |
| Browse, search, add, edit books | yes | yes |
| Delete books and members | no | yes |
| Browse, add, edit members | yes | yes |
| Borrow and return books | yes | yes |
| Create, promote and delete staff accounts | no | yes |
| Change own password | yes | yes |

Staff do not merely hide the delete buttons. The route itself answers `403 Forbidden`, so
typing the URL by hand changes nothing. An administrator cannot delete their own account,
which stops the last administrator locking everyone out.

## Testing

```bash
python -m unittest discover -s tests -t .    # 90 unit tests
python -m gui.smoke_test                     # builds every GUI widget, then exits
python web/live_check.py                     # 35 checks against a real HTTP server
```

The unit tests use Flask's in-process test client. `web/live_check.py` is the other half:
it starts a real server on a spare port, drives it with real requests and real cookies, and
prints one PASS/FAIL line per check. It works in a throwaway data folder, so running it
never touches your own `data/` files. Use it after changing a template or a stylesheet,
where a broken link or a missing static file would not show up in a unit test.

## Project structure

```
Library-Management-System/
├── main.py                  entry point: console, --gui, --demo, --web
├── demo_console.py          the same system in a single file, for reading
├── requirements.txt         Flask, needed only by the web dashboard
│
├── models/                  the data and the rules attached to it
│   ├── book.py              Book
│   ├── member.py            Member (base class)
│   ├── student.py           StudentMember
│   ├── teacher.py           TeacherMember
│   ├── user.py              User, roles, PBKDF2 password hashing
│   ├── validators.py        shared input checking
│   └── __init__.py          member_from_dict: rebuilds the right subclass
│
├── services/
│   ├── library.py           Library: composition, borrow/return/search
│   └── permissions.py       the role table the whole app asks
│
├── storage/
│   └── json_storage.py      reads and writes books, members and users
│
├── gui/
│   └── app.py               Tkinter application
│
├── web/
│   ├── app.py               Flask application factory
│   ├── views.py             every route
│   ├── security.py          login, CSRF and the capability guards
│   ├── live_check.py        end-to-end check against a real server
│   ├── templates/           Jinja templates
│   └── static/style.css
│
├── data/
│   ├── books.json           the catalogue
│   ├── members.json         the members and the books they hold
│   └── users.json           accounts (created on first run, never committed)
│
└── tests/
    ├── test_library.py      33 tests: the rules and the storage layer
    └── test_web.py          57 tests: logins, roles, CSRF, every route
```

The layers only depend downwards: `gui`, `web` and `main` use `services`; `services` uses
`models` and `storage`; `models` knows nothing about the others. That is why one `Library`
object can be driven from a console menu, from a window and from a browser.

## Screens

The desktop app shows a title, six action buttons, a search bar and a `ttk.Treeview`
table of books, with a second tab for the members. Borrowed books are shown in orange,
members who have reached their limit in red.

```
┌──────────────────────────────────────────────────┐
│             LIBRARY MANAGEMENT SYSTEM            │
│  My School Library                              │
├──────────────────────────────────────────────────┤
│  [ Add Book ]     [ Add Member ]                 │
│  [ Borrow Book ]  [ Return Book ]                │
│  [ Search Book ]  [ View Members ]               │
├──────────────────────────────────────────────────┤
│ Search: [____________________] [Search] [Clear]   │
├──────────────────────────────────────────────────┤
│ ID │ Title              │ Author       │ Status  │
│────┼────────────────────┼──────────────┼─────────│
│101 │ Python Programming │ John Smith   │Available│
│102 │ Data Structures    │ Robert Brown │Borrowed │
└──────────────────────────────────────────────────┘
```

The web dashboard has a header, a nav bar that only offers what the signed-in role may
use, a row of count cards, and pages for books, members, staff accounts and your own
profile.

## Object-oriented design

**Classes and objects.** `Book`, `Member` and `User` hold their own data and the methods
that act on it. `Library` holds lists of all three: composition, one object containing
others.

**Encapsulation.** A member's borrowed books live in `self.__borrowed_books`. The double
underscore makes Python hide the attribute, so the only way in is `add_borrowed_book()`,
`remove_borrowed_book()` or `get_borrowed_books()`. A caller that receives the list from
`get_borrowed_books()` gets a copy and cannot corrupt the member. `Book.is_available` is a
property, so the availability flag is never set to something meaningless.

**Inheritance.** `StudentMember` and `TeacherMember` extend `Member` and change only the
numbers.

**Polymorphism.** One call, different answers:

```python
for member in library.members:
    print(member.name, "can borrow", member.borrowing_limit(), "books")

# Mg Mg can borrow 3 books
# U Aung can borrow 10 books
```

The loop does not check the type of the object, because it does not have to.

**One object, many front ends.** Every action returns an `OperationResult`, which holds a
success flag and a message. The console prints `result.message`, the GUI puts the same text
in a message box, and the web dashboard turns it into a green or red banner. The rules live
in one place and are never repeated.

**Permissions as a table.** Each role maps to a set of capability names. Views ask
`can(current_user, "books.delete")` instead of `if user.role == "admin"`, so a rule is
written once and adding a third role later is a change to a single dictionary.

## Security

- Passwords are hashed with PBKDF2-SHA256, 240,000 rounds, and a random salt per account.
  The plain password is never written anywhere. `User.check_password()` uses
  `hmac.compare_digest`, so a comparison cannot be timed.
- Every `POST` is rejected unless it carries the session's CSRF token.
- A login that is missing a token, or a redirect to a site outside this app, is refused.
- Password changes need the current password. An administrator cannot delete their own
  account.

`SECRET_KEY` is read from the environment. When it is not set, a random one is generated
at each start, which is fine for local use but logs everyone out on every restart:

```bash
SECRET_KEY=some-long-random-string python main.py --web     # macOS and Linux
$env:SECRET_KEY="some-long-random-string"; python main.py --web   # Windows
```

## Business rules

- A book can only be borrowed by one member at a time.
- A member cannot borrow the same book twice.
- A member cannot go past their limit (3 for a student, 10 for a teacher).
- A book can only be returned by the member who borrowed it.
- A borrowed book cannot be deleted, and a member with books cannot be deleted.
- Book IDs and member IDs are unique.

## Data files

`data/books.json`

```json
[
    {
        "book_id": 101,
        "title": "Python Programming",
        "author": "John Smith",
        "category": "Programming",
        "is_available": true
    }
]
```

`data/members.json` stores the *ids* of the books a member holds rather than a second copy
of each book, so the two files can never disagree:

```json
[
    {
        "member_id": 1,
        "name": "Mg Mg",
        "email": "mgmg@gmail.com",
        "member_type": "Student",
        "borrowed_book_ids": [102, 103]
    }
]
```

`data/users.json` holds the accounts. Each password is a salt and a hash, never the
password:

```json
[
    {
        "username": "admin",
        "full_name": "Library Administrator",
        "role": "admin",
        "password_hash": "pbkdf2_sha256$<salt>$<hash>"
    }
]
```

On the first run the files are filled with six example books, three members and the two
accounts above. A file that is empty or damaged is repaired instead of crashing the
program. `data/users.json` is in `.gitignore`, because it holds the accounts of whoever
clones the repository; the app creates it on demand.

## License

MIT
