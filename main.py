from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# Konfigurasi koneksi database MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="crud_db"
)

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
    
    cursor = db.cursor()
    cursor.execute("INSERT INTO items (name, description) VALUES (%s, %s)", (name, description))
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
        
        cursor.execute("UPDATE items SET name = %s, description = %s WHERE id = %s", (name, description, item_id))
        db.commit()
        
        return redirect('/')

# Route untuk menghapus item
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete(item_id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    db.commit()
    
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
