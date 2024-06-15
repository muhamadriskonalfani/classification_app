from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import mysql.connector
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Konfigurasi koneksi database MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="crud_db"
)

# Lokasi penyimpanan file yang diupload
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # Maksimal ukuran file 16MB

# Endpoint untuk melayani file statis
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route untuk halaman utama, menampilkan daftar item
@app.route('/')
def index():
    cursor = db.cursor()
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    return render_template('index.html', items=items)

# Route untuk menambahkan item baru
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    description = request.form['description']
    file = request.files['image']

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
    else:
        filename = None
    
    cursor = db.cursor()
    cursor.execute("INSERT INTO items (name, description, image) VALUES (%s, %s, %s)", (name, description, filename))
    db.commit()
    
    return redirect('/')

# Route untuk mengedit item
@app.route('/edit/<int:item_id>', methods=['GET', 'POST'])
def edit(item_id):
    cursor = db.cursor()
    if request.method == 'GET':
        cursor.execute("SELECT * FROM items WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        return render_template('edit.html', item=item)
    elif request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        file = request.files['image']

        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            cursor.execute("UPDATE items SET name = %s, description = %s, image = %s WHERE id = %s", (name, description, filename, item_id))
        else:
            cursor.execute("UPDATE items SET name = %s, description = %s WHERE id = %s", (name, description, item_id))
        
        db.commit()
        
        return redirect('/')

# Route untuk menghapus item
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    cursor = db.cursor()
    cursor.execute("SELECT image FROM items WHERE id = %s", (item_id,))
    image = cursor.fetchone()[0]
    if image:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image))
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    db.commit()
    
    return redirect('/')

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
