import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import sqlite3
from datetime import datetime
from database import get_db, init_db, row_to_dict

app = Flask(__name__)
CORS(app)  # Izinkan akses dari frontend

init_db()

# ==================== Helper Functions ====================
def execute_query(query, args=(), one=False):
    conn = get_db()
    cur = conn.execute(query, args)
    rv = [row_to_dict(row) for row in cur.fetchall()]
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

def execute_insert(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def execute_update_delete(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected

# ==================== Products ====================
@app.route('/api/products', methods=['GET'])
def get_products():
    products = execute_query('SELECT * FROM products ORDER BY name')
    return jsonify(products)

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
        new_product = execute_query('SELECT * FROM products WHERE id = ?', (last_id,), one=True)
        return jsonify(new_product), 201
    except sqlite3.IntegrityError as e:
        return jsonify({'error': 'Kode produk sudah ada'}), 409

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    data = request.json
    required = ['name', 'code', 'category', 'flex', 'catcode']
    if not all(k in data for k in required):
        return jsonify({'error': 'Data tidak lengkap'}), 400
    
    now = datetime.now().isoformat()
    try:
        affected = execute_update_delete('''
            UPDATE products SET name=?, code=?, category=?, flex=?, catcode=?, image=?, updated_at=?
            WHERE id=?
        ''', (data['name'], data['code'], data['category'], data['flex'], data['catcode'],
              data.get('image', ''), now, id))
        if affected == 0:
            return jsonify({'error': 'Produk tidak ditemukan'}), 404
        updated = execute_query('SELECT * FROM products WHERE id = ?', (id,), one=True)
        return jsonify(updated)
    except sqlite3.IntegrityError as e:
        return jsonify({'error': 'Kode produk sudah ada'}), 409

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    affected = execute_update_delete('DELETE FROM products WHERE id = ?', (id,))
    if affected == 0:
        return jsonify({'error': 'Produk tidak ditemukan'}), 404
    return jsonify({'success': True})

# ==================== Categories ====================
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = execute_query('SELECT * FROM categories ORDER BY name')
    return jsonify(categories)

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
        new_cat = execute_query('SELECT * FROM categories WHERE id = ?', (last_id,), one=True)
        return jsonify(new_cat), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nama kategori sudah ada'}), 409

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    data = request.json
    if not data.get('name'):
        return jsonify({'error': 'Nama kategori harus diisi'}), 400
    
    now = datetime.now().isoformat()
    try:
        affected = execute_update_delete('''
            UPDATE categories SET name=?, image=?, updated_at=? WHERE id=?
        ''', (data['name'], data.get('image', ''), now, id))
        if affected == 0:
            return jsonify({'error': 'Kategori tidak ditemukan'}), 404
        updated = execute_query('SELECT * FROM categories WHERE id = ?', (id,), one=True)
        return jsonify(updated)
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Nama kategori sudah ada'}), 409

@app.route('/api/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    # Ambil nama kategori sebelum dihapus untuk update produk
    cat = execute_query('SELECT name FROM categories WHERE id = ?', (id,), one=True)
    if not cat:
        return jsonify({'error': 'Kategori tidak ditemukan'}), 404
    
    # Update produk dengan kategori ini menjadi 'Lainnya'
    execute_update_delete('UPDATE products SET category = ? WHERE category = ?', ('Lainnya', cat['name']))
    
    affected = execute_update_delete('DELETE FROM categories WHERE id = ?', (id,))
    return jsonify({'success': True})

# ==================== Settings ====================
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
        # Simpan sebagai JSON string
        json_value = json.dumps(value)
        execute_update_delete('''
            INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
        ''', (key, json_value, now))
    return jsonify({'success': True})

# ==================== Export / Import ====================
@app.route('/api/export', methods=['POST'])
def export_data():
    products = execute_query('SELECT * FROM products')
    categories = execute_query('SELECT * FROM categories')
    settings = execute_query('SELECT * FROM settings')
    export = {
        'products': products,
        'categories': categories,
        'settings': settings,
        'export_date': datetime.now().isoformat()
    }
    return jsonify(export)

@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.json
    if not data or 'products' not in data:
        return jsonify({'error': 'Data tidak valid'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Hapus semua data lama
    cursor.execute('DELETE FROM products')
    cursor.execute('DELETE FROM categories')
    cursor.execute('DELETE FROM settings')
    
    # Import products
    for product in data['products']:
        cursor.execute('''
            INSERT INTO products (id, name, code, category, flex, catcode, image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product.get('id'), product['name'], product['code'], product['category'],
              product['flex'], product['catcode'], product.get('image', ''),
              product.get('created_at'), product.get('updated_at')))
    
    # Import categories
    for cat in data.get('categories', []):
        cursor.execute('''
            INSERT INTO categories (id, name, image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (cat.get('id'), cat['name'], cat.get('image', ''),
              cat.get('created_at'), cat.get('updated_at')))
    
    # Import settings
    for setting in data.get('settings', []):
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
        ''', (setting['key'], setting['value'], setting.get('updated_at')))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    # Untuk menjalankan langsung (development)
    port = int(os.environ.get('PORT', 5000))
    # Gunakan host='0.0.0.0' agar bisa diakses dari luar container
    app.run(host='0.0.0.0', port=port, debug=True)
