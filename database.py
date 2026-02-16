import sqlite3
import os
import sys

# Gunakan environment variable DATABASE_PATH jika ada, jika tidak gunakan folder /tmp agar writable di container
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join('/tmp', 'pos.db'))

def get_db():
    """Mendapatkan koneksi database dengan row_factory"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"[ERROR] Gagal konek ke database: {e}", file=sys.stderr)
        raise

def init_db():
    """Inisialisasi database: membuat tabel jika belum ada"""
    try:
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
        print(f"[INFO] Database initialized successfully at {DB_PATH}", file=sys.stderr)
    except Exception as e:
        print(f"[FATAL] Database initialization error: {e}", file=sys.stderr)
        raise  # Penting: biarkan error naik agar aplikasi gagal start

def row_to_dict(row):
    """Konversi sqlite3.Row ke dictionary"""
    return {key: row[key] for key in row.keys()}
