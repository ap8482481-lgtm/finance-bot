import sqlite3
import os

DB_PATH = os.path.join(os.getenv("DATA_DIR", "."), "finance.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            category TEXT,
            amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Безопасное добавление новой колонки для комментариев (если её еще нет в старой базе)
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN note TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass # Колонка уже существует
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reserves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT,
            amount REAL
        )
    ''')
    conn.commit()
    conn.close()

def add_transaction(t_type, category, amount, note=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO transactions (type, category, amount, note) VALUES (?, ?, ?, ?)", (t_type, category, amount, note))
    conn.commit()
    conn.close()

def get_total_income():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='income'")
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0.0

def get_total_expenses():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM transactions WHERE type='expense'")
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0.0

def add_reserve(amount, target):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO reserves (target, amount) VALUES (?, ?)", (target, amount))
    conn.commit()
    conn.close()

def get_total_reserve():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount) FROM reserves")
    res = cursor.fetchone()[0]
    conn.close()
    return res if res else 0.0

def get_all_reserves_with_id():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, target, amount FROM reserves")
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_reserve_by_id(reserve_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reserves WHERE id = ?", (reserve_id,))
    conn.commit()
    conn.close()

def execute_reserve(target):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT SUM(amount) FROM reserves WHERE target = ?", (target,))
    amount = cursor.fetchone()[0]
    
    if amount:
        cat_name = f"✅ Оплата резерва: {target.title()}"
        cursor.execute("INSERT INTO transactions (type, category, amount, note) VALUES (?, ?, ?, ?)", ("expense", cat_name, amount, ""))
        cursor.execute("DELETE FROM reserves WHERE target = ?", (target,))
        
    conn.commit()
    conn.close()
    return amount

def get_recent_transactions(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT type, category, amount, date, note FROM transactions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_last_transaction():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, category, amount FROM transactions ORDER BY id DESC LIMIT 1")
    last = cursor.fetchone()
    if last:
        cursor.execute("DELETE FROM transactions WHERE id = ?", (last[0],))
        conn.commit()
        conn.close()
        return last
    conn.close()
    return None

def get_expenses_by_category():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='expense' GROUP BY category")
    rows = cursor.fetchall()
    conn.close()
    return rows
