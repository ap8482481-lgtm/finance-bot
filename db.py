import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            category TEXT,
            amount REAL,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_transaction(t_type: str, category: str, amount: float):
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)",
        (t_type, category, amount, date_now)
    )
    conn.commit()
    conn.close()

def get_total_expenses() -> float:
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0.0

def add_income(amount: float):
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)",
        ("income", "Пополнение", amount, date_now)
    )
    conn.commit()
    conn.close()

def get_total_income() -> float:
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0.0

def add_reserve(amount: float, name: str):
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)",
        ("reserve", name, amount, date_now)
    )
    conn.commit()
    conn.close()

def get_total_reserve() -> float:
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='reserve'")
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0.0

def execute_reserve(name: str):
    conn = sqlite3.connect('budget.db')
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM transactions WHERE type='reserve' AND category=? ORDER BY id DESC LIMIT 1", (name,))
    result = cursor.fetchone()
    if result:
        amount = result[0]
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)", ("expense", f"Платеж: {name}", amount, date_now))
        cursor.execute("INSERT INTO transactions (type, category, amount, date) VALUES (?, ?, ?, ?)", ("reserve", f"Оплачено: {name}", -amount, date_now))
        conn.commit()
    conn.close()