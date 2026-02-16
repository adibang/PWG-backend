import os
import sys
import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==================== KONFIGURASI DATABASE ====================
DB_PATH = os.environ.get('DATABASE_PATH', '/tmp/pos.db')

def get_db():
    """Mendapatkan koneksi database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"[ERROR] Gagal konek DB: {e}", file=sys.stderr)
        raise

def init_db():
    """Inisialisasi tabel jika belum ada"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
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
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                image TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        c.execute('''
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
        print(f"[INFO] Database siap di {DB_PATH}", file=sys.stderr)
    except Exception as e:
        print(f"[FATAL] Gagal inisialisasi DB: {e}", file=sys.stderr)
        sys.exit(1)

init_db()

def row_to_dict(row):
    return {key: row[key] for key in row.keys()}

def execute_query(query, args=(), one=False):
    conn = get_db()
    cur = conn.execute(query, args)
    rows = [row_to_dict(row) for row in cur.fetchall()]
    conn.commit()
    conn.close()
    if one and rows:
        return rows[0]
    return rows

def execute_insert(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def execute_update(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected

# ==================== ROUTES DASAR ====================
@app.route('/')
def home():
    return jsonify({'status': 'ok', 'message': 'POS Barcode API is running'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'time': datetime.now().isoformat()})

# ==================== PRODUK ====================
@app.route('/api/products', methods=['GET'])
def get_products():
    return jsonify(execute_query('SELECT * FROM products ORDER BY name'))

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    required = ['name', 'code', 'category', 'flex', 'catcode']
    if not all(k in data for k in required):
        return jsonify({'error': 'Data tidak lengkap'}), 400
    
    now = datetime.now().isoformat()
    try:
        last_id = execute_insert('''
            INSERT INTO products (name, code, category, flex, catcode, image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['code'], data['category'], data['flex'], data['catcode'],
              data.get('image', ''), now, now))
        return jsonify(execute_query('SELECT * FROM products WHERE id = ?', (last_id,), one=True)), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Kode produk sudah ada'}), 409

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    data = request.json
    required = ['name', 'code', 'category', 'flex', 'catcode']
    if not all(k in data for k in required):
        return jsonify({'error': 'Data tidak lengkap'}), 400
    
    now = datetime.now().isoformat()
    try:
        affected = execute_update('''
            UPDATE products SET name=?, code=?, category=?, flex=?, catcode=?, image=?, updated_at=?
            WHERE id=?
        ''', (data['name'], data['code'], data['category'], data['flex'], data['catcode'],
              data.get('image', ''), now, id))
        if affected == 0:
            return jsonify({'error': 'Produk tidak ditemukan'}), 404
        return jsonify(execute_query('SELECT * FROM products WHERE id = ?', (id,), one=True))
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Kode produk sudah ada'}), 409

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    affected = execute_update('DELETE FROM products WHERE id = ?', (id,))
    if affected == 0:
        return jsonify({'error': 'Produk tidak ditemukan'}), 404
    return jsonify({'success': True})

# ==================== KATEGORI ====================
@app.route('/api/categories', methods=['GET'])
def get_categories():
    return jsonify(execute_query('SELECT * FROM categories ORDER BY name'))

@app.route('/api/categories', methods=['POST'])
def add_category():
    data = request.json
    if not data.get('name'):
        return jsonify({'error': 'Nama kategori harus diisi'}), 400
    
    now = datetime.now().isoformat()
    try:
        last_id = execute_insert('''
            INSERT INTO categories (name, image, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        ''', (data['name'], data.get('image', ''), now, now))
        return jsonify(execute_query('SELECT * FROM categories WHERE id = ?', (last_id,), one=True)), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nama kategori sudah ada'}), 409

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    data = request.json
    if not data.get('name'):
        return jsonify({'error': 'Nama kategori harus diisi'}), 400
    
    now = datetime.now().isoformat()
    try:
        affected = execute_update('''
            UPDATE categories SET name=?, image=?, updated_at=? WHERE id=?
        ''', (data['name'], data.get('image', ''), now, id))
        if affected == 0:
            return jsonify({'error': 'Kategori tidak ditemukan'}), 404
        return jsonify(execute_query('SELECT * FROM categories WHERE id = ?', (id,), one=True))
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nama kategori sudah ada'}), 409

@app.route('/api/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    cat = execute_query('SELECT name FROM categories WHERE id = ?', (id,), one=True)
    if not cat:
        return jsonify({'error': 'Kategori tidak ditemukan'}), 404
    
    execute_update('UPDATE products SET category = ? WHERE category = ?', ('Lainnya', cat['name']))
    affected = execute_update('DELETE FROM categories WHERE id = ?', (id,))
    return jsonify({'success': True})

# ==================== PENGATURAN ====================
@app.route('/api/settings', methods=['GET'])
def get_settings():
    rows = execute_query('SELECT * FROM settings')
    settings = {row['key']: json.loads(row['value']) for row in rows}
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    now = datetime.now().isoformat()
    for key, value in data.items():
        json_value = json.dumps(value)
        execute_update('''
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        ''', (key, json_value, now))
    return jsonify({'success': True})

# ==================== EKSPOR / IMPOR ====================
@app.route('/api/export', methods=['POST'])
def export_data():
    return jsonify({
        'products': execute_query('SELECT * FROM products'),
        'categories': execute_query('SELECT * FROM categories'),
        'settings': execute_query('SELECT * FROM settings'),
        'export_date': datetime.now().isoformat()
    })

@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.json
    if not data or 'products' not in data:
        return jsonify({'error': 'Data tidak valid'}), 400
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM products')
    cur.execute('DELETE FROM categories')
    cur.execute('DELETE FROM settings')
    
    for p in data['products']:
        cur.execute('''
            INSERT INTO products (id, name, code, category, flex, catcode, image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (p.get('id'), p['name'], p['code'], p['category'], p['flex'], p['catcode'],
              p.get('image', ''), p.get('created_at'), p.get('updated_at')))
    
    for c in data.get('categories', []):
        cur.execute('''
            INSERT INTO categories (id, name, image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (c.get('id'), c['name'], c.get('image', ''), c.get('created_at'), c.get('updated_at')))
    
    for s in data.get('settings', []):
        cur.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (s['key'], s['value'], s.get('updated_at')))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[INFO] Menjalankan Flask di port {port}", file=sys.stderr)
    app.run(host='0.0.0.0', port=port, debug=False)
