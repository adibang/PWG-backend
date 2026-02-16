import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'pos.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Tabel products
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            flex TEXT NOT NULL,
            catcode TEXT NOT NULL,
            image TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # Tabel categories
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            image TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # Tabel settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # Tabel print_history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS print_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT,
            product_name TEXT,
            weight TEXT,
            timestamp TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def row_to_dict(row):
    return {key: row[key] for key in row.keys()}
