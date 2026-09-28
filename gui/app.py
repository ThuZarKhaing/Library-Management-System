"""The Tkinter desktop application.

    python main.py --gui

Widgets used: Label, Button, Entry, Combobox, Treeview, Notebook, Messagebox.
Every button calls the same Library methods the console uses, so the two
front ends can never disagree.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from models import Book, StudentMember, TeacherMember, ValidationError

MEMBER_CLASSES = {
    "Student": StudentMember,
    "Teacher": TeacherMember,
}

BOOK_COLUMNS = ("book_id", "title", "author", "category", "status")
BOOK_HEADINGS = {
    "book_id": "ID",
    "title": "Title",
    "author": "Author",
    "category": "Category",
    "status": "Status",
}

MEMBER_COLUMNS = ("member_id", "name", "email", "member_type", "borrowed", "limit")
MEMBER_HEADINGS = {
    "member_id": "ID",
    "name": "Name",
    "email": "Email",
    "member_type": "Type",
    "borrowed": "Borrowed",
    "limit": "Limit",
}


class FormDialog(tk.Toplevel):
    """A small popup with labelled fields and OK / Cancel.

    ``fields`` is a list of dictionaries:

        {"key": "title", "label": "Title", "type": "entry", "default": ""}
        {"key": "book_id", "label": "Book ID", "type": "int"}
        {"key": "member_type", "type": "choice", "choices": ["Student", ...]}

    ``on_submit(values)`` returns None to close the window, or an error string
    to keep it open and show the problem.
    """

    def __init__(self, parent, title, fields, on_submit, on_success):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self.on_submit = on_submit
        self.on_success = on_success
        self.variables = {}
        self.first_input = None

        frame = ttk.Frame(self, padding=14)
        frame.grid(row=0, column=0, sticky="nsew")

        for row, field in enumerate(fields):
            ttk.Label(frame, text=field["label"] + ":").grid(
                row=row, column=0, sticky="w", padx=(0, 8), pady=4
            )
            variable, widget = self._make_widget(frame, field)
            self.variables[field["key"]] = variable
            widget.grid(row=row, column=1, sticky="ew", pady=4)
            if self.first_input is None:
                self.first_input = widget

        self.error_label = ttk.Label(
            frame, text="", foreground="#b00020", wraplength=380, justify="left"
        )
        self.error_label.grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(6, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=(6, 0))
        ttk.Button(buttons, text="OK", command=self._handle_ok).pack(side="right")

        self.bind("<Return>", lambda _event: self._handle_ok())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.update_idletasks()
        self.grab_set()
        if self.first_input is not None:
            self.first_input.focus_set()
            if isinstance(self.first_input, ttk.Entry):
                self.first_input.select_range(0, "end")

    def _make_widget(self, parent, field):
        if field.get("type") == "choice":
            choices = field["choices"]
            variable = tk.StringVar(value=field.get("default", choices[0] if choices else ""))
            return variable, ttk.Combobox(
                parent, textvariable=variable, values=choices, state="readonly", width=32
            )
        variable = tk.StringVar(value=str(field.get("default", "")))
        return variable, ttk.Entry(parent, textvariable=variable, width=34)

    def _handle_ok(self):
        values = {key: variable.get() for key, variable in self.variables.items()}
        error = self.on_submit(values)
        if error:
            self.error_label.configure(text=error)
            return
        self.error_label.configure(text="")
        self.on_success()
        self.destroy()


class BorrowDialog(FormDialog):
    """Pick a member and a book, for both borrowing and returning."""

    def __init__(self, parent, title, member_options, book_options, on_success, submit_message):
        labels = {}
        for value, text in member_options:
            labels[text] = value
        for value, text in book_options:
            labels[text] = value

        def submit(values):
            try:
                member_id = int(labels.get(values["member"], ""))
                book_id = int(labels.get(values["book"], ""))
            except (TypeError, ValueError):
                return "Please choose both a member and a book."
            result = submit_message(member_id, book_id)
            return None if result else result.message

        fields = [
            {
                "key": "member",
                "label": "Member",
                "type": "choice",
                "choices": [text for _, text in member_options] or ["No members yet"],
            },
            {
                "key": "book",
                "label": "Book",
                "type": "choice",
                "choices": [text for _, text in book_options] or ["No books yet"],
            },
        ]
        super().__init__(parent, title, fields, submit, on_success)


class LibraryApp(ttk.Frame):
    """The whole window: buttons on top, tables below."""

    def __init__(self, master, library):
        super().__init__(master, padding=10)
        self.library = library

        self._build_header()
        self._build_actions()
        self._build_notebook()
        self._build_search()
        self._build_status_bar()

        self.pack(fill="both", expand=True)
        self.refresh()

    # --------------------------------------------------------------- building
    def _build_header(self):
        header = ttk.LabelFrame(self, text=" ")
        header.pack(fill="x")
        ttk.Label(header, text="LIBRARY MANAGEMENT SYSTEM", font=("Segoe UI", 16, "bold")).pack(
            pady=(8, 2)
        )
        ttk.Label(header, text=self.library.name).pack(pady=(0, 8))

    def _build_actions(self):
        panel = ttk.LabelFrame(self, text=" Actions ", padding=8)
        panel.pack(fill="x", pady=(10, 0))

        buttons = [
            ("Add Book", self.open_add_book),
            ("Add Member", self.open_add_member),
            ("Borrow Book", self.open_borrow_book),
            ("Return Book", self.open_return_book),
            ("Search Book", self.focus_search),
            ("View Members", self.show_members_tab),
        ]
        for index, (label, command) in enumerate(buttons):
            ttk.Button(panel, text=label, command=command, width=18).grid(
                row=index // 2, column=index % 2, padx=6, pady=4, sticky="ew"
            )
        panel.columnconfigure(0, weight=1)
        panel.columnconfigure(1, weight=1)

    def _build_search(self):
        panel = ttk.Frame(self)
        panel.pack(fill="x", pady=(10, 6))
        ttk.Label(panel, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(panel, textvariable=self.search_var, width=32)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda _event: self.refresh_books())
        self.search_entry = entry
        ttk.Button(panel, text="Search", command=self.refresh_books).pack(side="left")
        ttk.Button(panel, text="Clear", command=self.clear_search).pack(side="left", padx=(6, 0))

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        books_tab = ttk.Frame(self.notebook, padding=6)
        members_tab = ttk.Frame(self.notebook, padding=6)
        self.notebook.add(books_tab, text="  Books  ")
        self.notebook.add(members_tab, text="  Members  ")

        self.book_tree = self._make_tree(
            books_tab,
            BOOK_COLUMNS,
            BOOK_HEADINGS,
            widths=(60, 260, 180, 160, 90),
            on_double_click=self.open_borrow_book,
        )
        self.member_tree = self._make_tree(
            members_tab,
            MEMBER_COLUMNS,
            MEMBER_HEADINGS,
            widths=(60, 160, 200, 90, 90, 70),
            on_double_click=self.open_return_book,
        )

    def _make_tree(self, parent, columns, headings, widths, on_double_click=None):
        holder = ttk.Frame(parent)
        holder.pack(fill="both", expand=True)

        tree = ttk.Treeview(holder, columns=columns, show="headings", selectmode="browse")
        for column, width in zip(columns, widths):
            tree.heading(column, text=headings[column])
            tree.column(column, width=width, anchor="w")
        tree.tag_configure("borrowed", foreground="#8a4b00")
        tree.tag_configure("full", foreground="#b00020")

        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if on_double_click is not None:
            tree.bind("<Double-1>", lambda _event: on_double_click())
        return tree

    def _build_status_bar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(8, 0))
        self.status_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.status_var).pack(side="left")
        ttk.Button(bar, text="Save now", command=self.save_now).pack(side="right")

    # -------------------------------------------------------------- refreshing
    def refresh(self):
        self.refresh_books()
        self.refresh_members()

    def clear_tabs(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    def refresh_books(self):
        keyword = self.search_var.get().strip()
        books = self.library.find_books(keyword)
        self.clear_tabs(self.book_tree)
        for book in books:
            tags = () if book.is_available else ("borrowed",)
            self.book_tree.insert(
                "",
                "end",
                values=(
                    book.book_id,
                    book.title,
                    book.author,
                    book.category,
                    book.status,
                ),
                tags=tags,
            )
        suffix = f' for "{keyword}"' if keyword else ""
        self.status_var.set(
            f"{len(books)} book(s) shown{suffix}  |  "
            f"{len(self.library.get_available_books())} available, "
            f"{len(self.library.get_borrowed_books())} borrowed"
        )

    def refresh_members(self):
        self.clear_tabs(self.member_tree)
        for member in self.library.members:
            tags = ("full",) if member.has_reached_limit() else ()
            self.member_tree.insert(
                "",
                "end",
                values=(
                    member.member_id,
                    member.name,
                    member.email,
                    member.member_type(),
                    member.borrowed_count(),
                    member.borrowing_limit(),
                ),
                tags=tags,
            )

    # ----------------------------------------------------------------- helpers
    def report(self, result):
        """Show the result of a Library action and refresh the tables."""
        self.refresh()
        if result:
            messagebox.showinfo(self.library.name, result.message, parent=self)
        else:
            messagebox.showwarning("Not possible", result.message, parent=self)

    def save_now(self):
        if self.library.save():
            messagebox.showinfo("Saved", "The data files have been updated.", parent=self)
        else:
            messagebox.showerror("Save failed", self.library.last_save_error, parent=self)

    def member_option_text(self, member):
        return f"{member.member_id}  -  {member.name} ({member.member_type()})"

    def book_option_text(self, book):
        return f"{book.book_id}  -  {book.title}"

    def _selected_ids(self):
        selection = self.book_tree.selection()
        if not selection:
            return None, None
        values = self.book_tree.item(selection[0], "values")
        return int(values[0]), values[1]

    # ----------------------------------------------------------------- actions
    def open_add_book(self):
        fields = [
            {"key": "book_id", "label": "Book ID", "type": "int", "default": self.library.next_book_id()},
            {"key": "title", "label": "Title"},
            {"key": "author", "label": "Author"},
            {"key": "category", "label": "Category", "default": "General"},
        ]
        done = {}

        def submit(values):
            try:
                book = Book(
                    values["book_id"], values["title"], values["author"], values["category"]
                )
            except ValidationError as error:
                return str(error)
            result = self.library.add_book(book)
            if not result:
                return result.message
            done["result"] = result
            return None

        FormDialog(self, "Add Book", fields, submit, lambda: self.report(done.get("result")))

    def open_add_member(self):
        fields = [
            {"key": "member_id", "label": "Member ID", "type": "int", "default": self.library.next_member_id()},
            {"key": "name", "label": "Name"},
            {"key": "email", "label": "Email"},
            {
                "key": "member_type",
                "label": "Member type",
                "type": "choice",
                "choices": list(MEMBER_CLASSES),
                "default": "Student",
            },
        ]
        done = {}

        def submit(values):
            try:
                member = MEMBER_CLASSES[values["member_type"]](
                    values["member_id"], values["name"], values["email"]
                )
            except ValidationError as error:
                return str(error)
            result = self.library.register_member(member)
            if not result:
                return result.message
            done["result"] = result
            return None

        FormDialog(self, "Add Member", fields, submit, lambda: self.report(done.get("result")))

    def open_borrow_book(self):
        if not self.library.members or not self.library.get_available_books():
            messagebox.showinfo(
                "Nothing to borrow",
                "You need at least one member and one available book.",
                parent=self,
            )
            return
        selected_book = self._selected_ids()[0]
        options = [
            (member.member_id, self.member_option_text(member)) for member in self.library.members
        ]
        book_options = [
            (book.book_id, self.book_option_text(book))
            for book in self.library.get_available_books()
        ]
        if selected_book is not None:
            book_options.sort(key=lambda item: item[0] != selected_book)

        BorrowDialog(
            self,
            "Borrow Book",
            options,
            book_options,
            self.refresh,
            self.library.borrow_book,
        )

    def open_return_book(self):
        if not self.library.get_borrowed_books():
            messagebox.showinfo("Nothing to return", "No book is currently borrowed.", parent=self)
            return
        borrowed = [
            (book.book_id, self.book_option_text(book)) for book in self.library.get_borrowed_books()
        ]
        holders = [
            (member.member_id, self.member_option_text(member))
            for member in self.library.members
            if member.borrowed_count()
        ]
        BorrowDialog(
            self,
            "Return Book",
            holders,
            borrowed,
            self.refresh,
            self.library.return_book,
        )

    def focus_search(self):
        self.notebook.select(0)
        self.search_entry.focus_set()

    def clear_search(self):
        self.search_var.set("")
        self.notebook.select(0)
        self.refresh_books()
        self.search_entry.focus_set()

    def show_members_tab(self):
        self.notebook.select(1)


def launch_gui(library):
    """Open the window. Call this from main.py with ``--gui``."""
    root = tk.Tk()
    root.title(f"{library.name} - Library Management System")
    root.geometry("900x520")
    root.minsize(720, 420)
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    app = LibraryApp(root, library)
    root.mainloop()
    return app
