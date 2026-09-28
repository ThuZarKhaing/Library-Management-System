"""Smoke test for the Tkinter layer: build every widget, then close it.

Tkinter needs a display, so this file is a manual check, not part of the
unittest suite:  python -m gui.smoke_test
"""

import tkinter as tk
from tkinter import ttk

from gui.app import FormDialog, LibraryApp
from services import Library
from storage import LibraryStorage


def build_library():
    library = Library("Smoke Test Library", storage=LibraryStorage())
    library.load()
    return library


def main():
    library = build_library()
    root = tk.Tk()
    root.withdraw()

    app = LibraryApp(root, library)
    app.update()
    app.refresh_books()
    app.search_var.set("Robert")
    app.refresh()
    app.show_members_tab()
    app.notebook.select(0)
    app.search_var.set("")

    rows = len(app.book_tree.get_children())
    members = len(app.member_tree.get_children())
    print(f"books in the table   : {rows}")
    print(f"members in the table : {members}")
    print(f"status bar           : {app.status_var.get()}")

    dialog = FormDialog(
        app,
        "Test Dialog",
        [
            {"key": "name", "label": "Name"},
            {"key": "kind", "label": "Kind", "type": "choice", "choices": ["A", "B"]},
        ],
        lambda values: "This is the error line." if values["name"] == "" else None,
        lambda: print("submitted ok"),
    )
    dialog._handle_ok()  # empty name -> dialog stays open and shows the error
    print("empty submit keeps the dialog open:", bool(dialog.winfo_exists()))
    print("error text shown                   :", repr(dialog.error_label.cget("text")))

    print("treeview columns   :", app.book_tree.cget("columns"))
    print("notebook tabs      :", [app.notebook.tab(i, "text") for i in app.notebook.tabs()])
    print("theme              :", ttk.Style(root).theme_use())

    # Borrow and return through the real dialogs, with no message boxes.
    def last_dialog():
        popups = [w for w in app.winfo_children() if isinstance(w, tk.Toplevel)]
        return popups[-1]

    app.notebook.select(0)
    app.open_borrow_book()
    borrow_dialog = last_dialog()
    borrow_dialog._handle_ok()
    print("after borrow dialog :", library.find_member(1).borrowed_count(), "book(s) held by member 1")
    borrow_dialog.destroy()

    app.open_return_book()
    return_dialog = last_dialog()
    return_dialog._handle_ok()
    print("after return dialog :", library.find_member(1).borrowed_count(), "book(s) held by member 1")
    return_dialog.destroy()

    app.destroy()
    root.destroy()
    print("GUI smoke test finished.")


if __name__ == "__main__":
    main()
