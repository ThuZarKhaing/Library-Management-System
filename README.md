# Library Management System

A desktop and console library system written in Python, built around object-oriented
programming: classes, encapsulation, inheritance, polymorphism, composition, lists of
objects, JSON persistence and a Tkinter GUI.

![Python](https://img.shields.io/badge/python-3.8%2B-blue) ![Tkinter](https://img.shields.io/badge/gui-tkinter-orange) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

| | |
|---|---|
| Add and remove books | ID, title, author, category |
| Register and remove members | Students and teachers |
| Borrow and return books | Availability and limits are checked automatically |
| Two member types | Student = 3 books, Teacher = 10 books (one method, two answers) |
| Live search | Filter by title, author or category as you type |
| Persistent storage | JSON files, written after every change |
| Two front ends | The same engine drives the console menu and the GUI |
| Test suite | 33 unit tests covering the rules and the storage layer |

## Screens

The GUI shows a title, six action buttons, a search bar and a `ttk.Treeview` table of
books, with a second tab for the members. Borrowed books are shown in orange, members
who have reached their limit in red.

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

## How to run

Requires Python 3.8 or newer. No third-party packages are needed; `tkinter` ships with
Python on Windows and macOS, and on Linux it comes from the `python3-tk` package.

```bash
git clone <your-repository-url>
cd "Library Management System"

python main.py            # console menu, data is saved automatically
python main.py --gui      # desktop application
python main.py --demo     # scripted tour of every rule, no typing needed
```

Run the tests:

```bash
python -m unittest discover -s tests -t .    # 33 tests
python -m gui.smoke_test                     # builds every GUI widget, then exits
```

## Project structure

```
Library Management System/
├── main.py                  entry point: console menu, --gui, --demo
├── demo_console.py          the same system in a single file, for reading
│
├── models/                  the data and the rules attached to it
│   ├── book.py              Book
│   ├── member.py            Member (base class)
│   ├── student.py           StudentMember
│   ├── teacher.py           TeacherMember
│   ├── validators.py        shared input checking
│   └── __init__.py          member_from_dict: rebuilds the right subclass
│
├── services/
│   └── library.py           Library: composition, borrow/return/search
│
├── storage/
│   └── json_storage.py      reads and writes books.json and members.json
│
├── gui/
│   └── app.py               Tkinter application
│
├── data/
│   ├── books.json           the catalogue
│   └── members.json         the members and the books they hold
│
└── tests/
    └── test_library.py      unit tests
```

The four layers only depend downwards: `gui` and `main` use `services`, `services` uses
`models` and `storage`, and `models` knows nothing about the others. That is why the same
`Library` object can be driven from a console menu and from a window.

## Object-oriented design

**Classes and objects.** `Book` and `Member` hold their own data and the methods that act
on it. `Library` holds lists of both: composition, one object containing others.

**Encapsulation.** A member's borrowed books live in `self.__borrowed_books`. The double
underscore makes Python hide the attribute, so the only way in is
`add_borrowed_book()`, `remove_borrowed_book()` or `get_borrowed_books()`. A caller that
receives the list from `get_borrowed_books()` gets a copy and cannot corrupt the member.
`Book.is_available` is a property, so the availability flag is never set to something
meaningless.

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

**One object, two front ends.** Every action returns an `OperationResult`, which holds a
success flag and a message. The console prints `result.message`; the GUI puts the same
text in a message box. The rules live in one place and are never repeated.

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

On the first run the files are filled with six example books and three members. A file
that is empty or damaged is repaired instead of crashing the program.

## Business rules

- A book can only be borrowed by one member at a time.
- A member cannot borrow the same book twice.
- A member cannot go past their limit (3 for a student, 10 for a teacher).
- A book can only be returned by the member who borrowed it.
- A borrowed book cannot be deleted, and a member with books cannot be deleted.
- Book IDs and member IDs are unique.

## License

MIT
