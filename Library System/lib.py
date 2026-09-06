"""
Library Management System
--------------------------
A simple, no-GUI, command-line Library Management System using Python and
an SQLite database (SQL database connectivity via Python's built-in sqlite3
module — no external database server required).

Features:
  1. Add books (name, author) to the library.
  2. Log a book being borrowed by a student (book, student name, class, date).
  3. Log a book being returned (adds a return date to the existing record).
  4. Search by book name -> shows book details + full borrow/return history.
  5. Search by student name -> shows that student's borrowing history.

Run:
    python library_system.py

Database file "library.db" is created automatically in the same folder.
"""

import sqlite3
from datetime import date

DB_NAME = "library.db"


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create the required tables if they don't already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            author TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrow_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            borrow_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books (book_id)
        )
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------

def add_book():
    name = input("Enter book name: ").strip()
    author = input("Enter author name: ").strip()

    if not name or not author:
        print("Book name and author cannot be empty.\n")
        return

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO books (name, author) VALUES (?, ?)", (name, author))
    conn.commit()
    conn.close()
    print(f'Book "{name}" by {author} added successfully.\n')


def find_book_by_name(cursor, name):
    """Return a list of books matching a (partial) name, case-insensitive."""
    cursor.execute(
        "SELECT book_id, name, author FROM books WHERE name LIKE ?",
        (f"%{name}%",)
    )
    return cursor.fetchall()


def choose_book(cursor, prompt_text="Enter book name: "):
    """Prompt for a book name, handle multiple matches, and return one book row."""
    name = input(prompt_text).strip()
    matches = find_book_by_name(cursor, name)

    if not matches:
        print(f'No book found matching "{name}".\n')
        return None

    if len(matches) == 1:
        return matches[0]

    print("\nMultiple matching books found:")
    for idx, (book_id, bname, author) in enumerate(matches, start=1):
        print(f"  {idx}. {bname}  (by {author})")

    choice = input("Select a book number: ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(matches)):
        print("Invalid selection.\n")
        return None

    return matches[int(choice) - 1]


def borrow_book():
    conn = get_connection()
    cursor = conn.cursor()

    book = choose_book(cursor, "Enter the name of the book being borrowed: ")
    if not book:
        conn.close()
        return

    book_id, book_name, author = book

    student_name = input("Enter student name: ").strip()
    student_class = input("Enter student class: ").strip()

    if not student_name or not student_class:
        print("Student name and class cannot be empty.\n")
        conn.close()
        return

    borrow_date = input(
        f"Enter borrow date (YYYY-MM-DD) [Enter for today, {date.today()}]: "
    ).strip()
    if not borrow_date:
        borrow_date = str(date.today())

    cursor.execute("""
        INSERT INTO borrow_records
            (book_id, student_name, student_class, borrow_date, return_date)
        VALUES (?, ?, ?, ?, NULL)
    """, (book_id, student_name, student_class, borrow_date))

    conn.commit()
    conn.close()
    print(f'"{book_name}" borrowed by {student_name} ({student_class}) on {borrow_date}.\n')


def return_book():
    conn = get_connection()
    cursor = conn.cursor()

    book = choose_book(cursor, "Enter the name of the book being returned: ")
    if not book:
        conn.close()
        return

    book_id, book_name, author = book

    # Find open (not yet returned) borrow records for this book
    cursor.execute("""
        SELECT record_id, student_name, student_class, borrow_date
        FROM borrow_records
        WHERE book_id = ? AND return_date IS NULL
        ORDER BY borrow_date
    """, (book_id,))
    open_records = cursor.fetchall()

    if not open_records:
        print(f'No outstanding (un-returned) borrow records for "{book_name}".\n')
        conn.close()
        return

    if len(open_records) == 1:
        record = open_records[0]
    else:
        print(f'\nMultiple students currently have "{book_name}" borrowed:')
        for idx, (rid, sname, sclass, bdate) in enumerate(open_records, start=1):
            print(f"  {idx}. {sname} ({sclass}) - borrowed on {bdate}")
        choice = input("Select the record number being returned: ").strip()
        if not choice.isdigit() or not (1 <= int(choice) <= len(open_records)):
            print("Invalid selection.\n")
            conn.close()
            return
        record = open_records[int(choice) - 1]

    record_id, student_name, student_class, borrow_date = record

    return_date = input(
        f"Enter return date (YYYY-MM-DD) [Enter for today, {date.today()}]: "
    ).strip()
    if not return_date:
        return_date = str(date.today())

    cursor.execute(
        "UPDATE borrow_records SET return_date = ? WHERE record_id = ?",
        (return_date, record_id)
    )
    conn.commit()
    conn.close()
    print(f'"{book_name}" returned by {student_name} ({student_class}) on {return_date}.\n')


# ---------------------------------------------------------------------------
# Search functions
# ---------------------------------------------------------------------------

def search_by_book():
    """Search for a book and show its details plus borrower/return history."""
    conn = get_connection()
    cursor = conn.cursor()

    name = input("Enter book name (or part of it) to search: ").strip()
    matches = find_book_by_name(cursor, name)

    if not matches:
        print(f'No book found matching "{name}".\n')
        conn.close()
        return

    for book_id, book_name, author in matches:
        print("\n" + "=" * 60)
        print(f"Book: {book_name}")
        print(f"Author: {author}")
        print("-" * 60)

        cursor.execute("""
            SELECT student_name, student_class, borrow_date, return_date
            FROM borrow_records
            WHERE book_id = ?
            ORDER BY borrow_date
        """, (book_id,))
        records = cursor.fetchall()

        if not records:
            print("No borrowing history for this book.")
        else:
            for sname, sclass, bdate, rdate in records:
                status = f"returned on {rdate}" if rdate else "not yet returned"
                print(f"  - {sname} ({sclass}) | borrowed: {bdate} | {status}")

        print("=" * 60)
    print()
    conn.close()


def search_by_student():
    """Search for a student and show their full borrowing history."""
    conn = get_connection()
    cursor = conn.cursor()

    name = input("Enter student name (or part of it) to search: ").strip()

    cursor.execute("""
        SELECT b.name, b.author, r.student_class, r.borrow_date, r.return_date
        FROM borrow_records r
        JOIN books b ON b.book_id = r.book_id
        WHERE r.student_name LIKE ?
        ORDER BY r.borrow_date
    """, (f"%{name}%",))
    records = cursor.fetchall()

    if not records:
        print(f'No borrowing history found for students matching "{name}".\n')
        conn.close()
        return

    print("\n" + "=" * 60)
    print(f'Borrowing history for students matching "{name}"')
    print("-" * 60)
    for book_name, author, sclass, bdate, rdate in records:
        status = f"returned on {rdate}" if rdate else "not yet returned"
        print(f'  - "{book_name}" by {author} | class: {sclass} | '
              f'borrowed: {bdate} | {status}')
    print("=" * 60 + "\n")

    conn.close()


def list_all_books():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, author FROM books ORDER BY name")
    books = cursor.fetchall()
    conn.close()

    if not books:
        print("No books in the library yet.\n")
        return

    print("\nAll books in the library:")
    for name, author in books:
        print(f"  - {name} (by {author})")
    print()

def view_all_history():
    """Show the full history of every borrow/return record in the system."""
    conn = get_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        SELECT b.name, b.author, r.student_name, r.student_class,
               r.borrow_date, r.return_date
        FROM borrow_records r
        JOIN books b ON b.book_id = r.book_id
        ORDER BY r.borrow_date
    """)
    records = cursor.fetchall()
    conn.close()
 
    if not records:
        print("No borrow/return history yet.\n")
        return
    print("\n" + "=" * 90)
    print("FULL BORROW / RETURN HISTORY")
    print("-" * 90)
    header = f'{"Book":25} {"Author":18} {"Borrower":15} {"Class":8} {"Borrowed":12} {"Returned":12}'
    print(header)
    print("-" * 90)
    for book_name, author, sname, sclass, bdate, rdate in records:
        rdate_display = rdate if rdate else "not returned"
        print(f'{book_name:25.25} {author:18.18} {sname:15.15} '
              f'{sclass:8.8} {bdate:12.12} {rdate_display:12.12}')
    print("=" * 90 + "\n")


# ---------------------------------------------------------------------------
# Menu / main loop
# ---------------------------------------------------------------------------

MENU = """
==============================
   LIBRARY MANAGEMENT SYSTEM
==============================
1. Add a new book
2. Log a book borrow
3. Log a book return
4. Search by book name  (shows borrowers & return dates)
5. Search by student name (shows borrow history)
6. List all books
7. View full borrow/return history
0. Exit
"""


def main():
    initialize_database()

    actions = {
        "1": add_book,
        "2": borrow_book,
        "3": return_book,
        "4": search_by_book,
        "5": search_by_student,
        "6": list_all_books,
        "7": view_all_history,
    }

    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye!")
            break

        action = actions.get(choice)
        if action:
            action()
        else:
            print("Invalid option. Please try again.\n")


if __name__ == "__main__":
    main()