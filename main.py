# DAFTAR PUSTAKA
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session, flash
import mysql.connector
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
from skimage.feature import hog
from sklearn import svm
from sklearn.model_selection import train_test_split
from datetime import datetime
from PIL import Image
import time
import bcrypt



# MEMBUAT INSTANCE APLIKASI FLASK
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])




# VARIABEL GLOBAL
db = None
file_url = ''
file_name = ''
file_path = ''
prediction = ''
file_resolution = ''
model = ''
progress = 0 
id_pengguna = ''
username = ''
connection = False
status_model = False
is_uploaded = False




# KONFIGURASI KONEKSI DATABASE MYSQL
def connect_to_database():
    global db, connection 
    
    try:
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="classification_app"
        )
        connection = True
    except mysql.connector.Error as err:
        print(f"Error ketika mencoba menghubungkan ke database: {err}")
        connection = False
    except Exception as e:
        print(f'Terjadi kesalahan: {str(e)}') 
        connection = False
        
connect_to_database() # Panggil fungsi koneksi database 




# DAFTAR FUNGSI PENDUKUNG

def hash_password(password):
    # Generate salt dan hash password menggunakan bcrypt
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    return hashed_password

def verify_password(stored_password, provided_password):
    # Verifikasi password menggunakan bcrypt
    return bcrypt.checkpw(provided_password.encode(), stored_password)

def generate_unique_filename(file_name, user_id):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name, extension = os.path.splitext(file_name)
    return f"{name}_{user_id}{timestamp}{extension}"

def update_progress(val, delay=0):
    global progress
    progress = val
    time.sleep(delay)
    
def loop_update_progress(start, end):
    for step in range(start, end):
        time.sleep(0.05)
        update_progress(step)

def delete_image(id_gambar, id_pengguna):
    cursor = None
    
    try:
        # Koneksi ke database
        cursor = db.cursor()
        
        # Eksekusi query
        cursor.execute("SELECT nama_unik_gambar FROM tb_gambar WHERE id_gambar = %s AND id_pengguna = %s", (id_gambar, id_pengguna))
        image = cursor.fetchone()
        
        if image:
            image_filename = image[0]
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            
            if os.path.exists(image_path):
                os.remove(image_path) 
        
        cursor.execute("DELETE FROM tb_gambar WHERE id_gambar = %s AND id_pengguna = %s", (id_gambar, id_pengguna))
        db.commit() 
    except mysql.connector.Error as err:
        flash(f'Kesalahan database: {err}')
        db.rollback()
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}') 
    finally:
        if cursor:
            cursor.close() 




# DAFTAR FUNGSI KLASIFIKASI

def load_images_from_folder(folder_path):
    images = []
    labels = []
    class_names = os.listdir(folder_path)
    for class_name in class_names:
        class_path = os.path.join(folder_path, class_name)
        if os.path.isdir(class_path):
            for filename in os.listdir(class_path):
                img_path = os.path.join(class_path, filename)
                img = cv2.imread(img_path)
                if img is not None:
                    images.append(img)
                    labels.append(class_name)
    return images, labels

def preprocess_image(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced_image = cv2.equalizeHist(gray_image)
    denoised_image = cv2.GaussianBlur(enhanced_image, (5, 5), 0)
    return denoised_image

def extract_hog_features(image):
    features, _ = hog(image, pixels_per_cell=(8, 8), cells_per_block=(2, 2), visualize=True)
    return features

def classify_new_image(image):
    resized_image = cv2.resize(image, (384, 128))
    gray_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
    enhanced_image = cv2.equalizeHist(gray_image)
    denoised_image = cv2.GaussianBlur(enhanced_image, (5, 5), 0)

    hog_features = extract_hog_features(denoised_image)
    hog_features = np.array(hog_features).reshape(1, -1)

    prediction = model.predict(hog_features)

    return prediction[0]

def klasifikasi_gambar_baru():
    global file_path, prediction
    
    update_progress(0, 1)  # Start progress

    # Langkah 8: Klasifikasi gambar baru
    new_image = cv2.imread(file_path)
    prediction = classify_new_image(new_image)

    update_progress(100, 1)  # Update progress
    update_progress(101, 1)  # Stop progress




# DAFTAR ENDPOINT

@app.route('/') # Halaman index
def index():
    global db, connection, id_pengguna, username 
    
    connect_to_database() # Panggil fungsi koneksi database 
    
    if 'id_pengguna' in session and 'username' in session:
        id_pengguna = session['id_pengguna']
        username = session['username']
        
    return render_template('index.html', connection=connection, id_pengguna=id_pengguna, username=username)

@app.route('/server_error') # Halaman server_error
def server_error(): 
    global db, connection
    
    connect_to_database() # Panggil fungsi koneksi database 
    
    return render_template('server_error.html', connection=connection)

@app.route('/login', methods=['GET', 'POST']) # Halaman login
def login():
    if request.method == 'POST':
        if 'login' in request.form:
            username = request.form['username']
            password = request.form['password']

            cursor = None 

            try:
                # Koneksi ke database
                cursor = db.cursor()

                # Eksekusi query
                query = "SELECT * FROM tb_pengguna WHERE username = %s"
                cursor.execute(query, (username,))
                user = cursor.fetchone()

                if user:
                    stored_password = user[2].encode('utf-8')
                    if verify_password(stored_password, password):
                        session['id_pengguna'] = user[0]
                        session['username'] = user[1]
                        return redirect(url_for('index'))
                    else:
                        flash('Password salah.') 
                else:
                    flash('Username tidak terdaftar.') 

            except mysql.connector.Error as err:
                flash(f'Kesalahan database: {err}')
            except Exception as e:
                flash(f'Terjadi kesalahan: {str(e)}')
            finally:
                if cursor:
                    cursor.close() 
        
        elif 'register' in request.form:
            new_username = request.form['new_username']
            new_password = request.form['new_password']

            # Hash password menggunakan bcrypt
            hashed_password = hash_password(new_password)

            cursor = None 
            
            try:
                # Koneksi ke database
                cursor = db.cursor()
                
                # Eksekusi query untuk menambahkan pengguna baru
                query = "INSERT INTO tb_pengguna (username, password) VALUES (%s, %s)"
                cursor.execute(query, (new_username, hashed_password))
                db.commit()
                flash('Registrasi berhasil. Silakan login.')
            except mysql.connector.Error as err:
                flash('Registrasi gagal. Username sudah digunakan.')
                db.rollback()
            except Exception as e:
                flash(f'Terjadi kesalahan: {str(e)}') 
            finally:
                if cursor:
                    cursor.close() 

    return render_template('login.html') 

@app.route('/logout') # Endpoint untuk logout
def logout():
    global id_pengguna, username, is_uploaded
    
    # Hapus semua variabel sesi yang terkait dengan pengguna
    session.pop('id_pengguna', None)
    session.pop('username', None)
    
    # Hapus nilai dari variabel global
    id_pengguna = ''
    username = ''
    is_uploaded = False
    
    return redirect(url_for('index'))

@app.route('/training_model') # Halaman latih model klasifikasi
def training_model():
    global username, status_model
    return render_template('training_model.html', username=username , status_model=status_model)

@app.route('/classification', methods=['GET', 'POST']) # Halaman utama klasifikasi
def classification():
    global id_pengguna, username, status_model, is_uploaded, progress
    
    progress = 0 
    cursor = None 
    
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tb_gambar WHERE id_pengguna = %s ORDER BY id_gambar DESC", (id_pengguna,))
        items = cursor.fetchall() 

    except mysql.connector.Error as err:
        flash(f'Kesalahan database: {err}')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}')
    finally:
        if cursor:
            cursor.close() 
    
    if not items:
        is_uploaded = False 
    
    return render_template('classification.html', id_pengguna=id_pengguna, username=username, status_model=status_model, is_uploaded=is_uploaded, items=items)

@app.route('/bantuan') # Halaman bantuan
def bantuan():
    global username, status_model
    return render_template('bantuan.html', username=username, status_model=status_model)

@app.route('/histori') # Halaman histori
def histori():
    global id_pengguna, username, status_model
    
    cursor = None 
    
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tb_gambar WHERE id_pengguna = %s ORDER BY id_gambar DESC", (id_pengguna,))
        items = cursor.fetchall() 

    except mysql.connector.Error as err:
        flash(f'Kesalahan database: {err}')
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}')
    finally:
        if cursor:
            cursor.close() 
    
    return render_template('histori.html', username=username, status_model=status_model, items=items)

@app.route('/add_to_database', methods=['GET', 'POST']) # Endpoint untuk menambah item
def add_to_database():
    global file_url, file_name, file_path, prediction, file_resolution, is_uploaded
    
    if request.method == 'POST':
        if 'submit' in request.form:
            user_id = request.form['id_pengguna']
            file = request.files.get('file')
            if file:
                file_name = file.filename
                unique_name = generate_unique_filename(file_name, user_id)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                file.save(file_path)
                file_url = url_for('static', filename=f'uploads/{unique_name}')
                img = Image.open(file)
                width, height = img.size
                file_resolution = f'{width}x{height}'
                klasifikasi_gambar_baru() 
    
    cursor = None
    
    try:
        # Koneksi ke database
        cursor = db.cursor()
        
        # Eksekusi query
        cursor.execute("INSERT INTO tb_gambar (id_pengguna, nama_unik_gambar, nama_gambar, status, resolusi) VALUES (%s, %s, %s, %s, %s)", (user_id, unique_name, file_name, prediction, file_resolution))
        db.commit()
        is_uploaded = True
    except mysql.connector.Error as err:
        flash(f'Kesalahan database: {err}')
        db.rollback()
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}') 
    finally:
        if cursor:
            cursor.close() 
    
    return redirect(url_for('classification')) 

@app.route('/delete/<int:id_gambar>/<int:id_pengguna>', methods=['POST']) # Endpoint untuk menghapus item dari halaman klasifikasi
def delete_from_homepage(id_gambar, id_pengguna):
    delete_image(id_gambar, id_pengguna)
    return redirect(url_for('classification'))

@app.route('/delete_history/<int:id_gambar>/<int:id_pengguna>', methods=['POST']) # Endpoint untuk menghapus item dari halaman histori
def delete_from_history(id_gambar, id_pengguna):
    delete_image(id_gambar, id_pengguna)
    return redirect(url_for('histori'))

@app.route('/delete_all_images/<int:id_pengguna>', methods=['POST']) # Endpoint untuk menghapus semua item
def delete_all_images(id_pengguna):
    cursor = None
    
    try:
        # Koneksi ke database
        cursor = db.cursor()
        
        # Eksekusi query
        cursor.execute("SELECT nama_unik_gambar FROM tb_gambar WHERE id_pengguna = %s", (id_pengguna,))
        images = cursor.fetchall()
        
        for image in images:
            if image:
                image_filename = image[0]
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                
                if os.path.exists(image_path):
                    os.remove(image_path) 
        
        cursor.execute("DELETE FROM tb_gambar WHERE id_pengguna = %s", (id_pengguna,))
        db.commit() 
    except mysql.connector.Error as err:
        flash(f'Kesalahan database: {err}')
        db.rollback()
    except Exception as e:
        flash(f'Terjadi kesalahan: {str(e)}') 
    finally:
        if cursor:
            cursor.close() 
    
    return redirect(url_for('classification')) 

@app.route('/uploads/<filename>') # Endpoint untuk melayani file statis
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/progress') # Endpoint untuk update kemajuan
def progress_status():
    global progress
    return jsonify({'progress': progress})

@app.route('/to_first_page') # Endpoint untuk ke halaman klasifikasi
def to_first_page(): 
    global is_uploaded
    is_uploaded = False
    return redirect(url_for('classification'))

@app.route('/to_second_page') # Endpoint untuk ke halaman 2 klasifikasi
def to_second_page(): 
    global is_uploaded
    is_uploaded = True
    return redirect(url_for('classification'))

@app.route('/latih_model_klasifikasi') # Endpoint untuk membuat model klasifikasi
def latih_model_klasifikasi():
    global model, status_model
    
    if model:
        status_model = True
        return jsonify({'status_model': status_model})
    else:
        try:
            update_progress(0, 1)  # Start progress
            loop_update_progress(1, 14)  # Update progress
            
            # Langkah 1: Memuat dataset dari folder lokal
            folder_path = './rice_leaf_diseases'
            images, labels = load_images_from_folder(folder_path)
            loop_update_progress(15, 27)  # Update progress

            # Langkah 2: Pra-pemrosesan setiap gambar
            preprocessed_images = [preprocess_image(cv2.resize(image, (384, 128))) for image in images]
            loop_update_progress(28, 37)  # Update progress

            # Langkah 3: Ekstraksi fitur HOG untuk setiap gambar yang sudah dipra-pemrosesan
            features = [extract_hog_features(image) for image in preprocessed_images]
            loop_update_progress(48, 60)  # Update progress

            # Langkah 4: Menyatukan fitur HOG menjadi satu array homogen
            X = np.array(features)
            y = np.array(labels)
            loop_update_progress(61, 73)  # Update progress

            # Langkah 5: Membagi dataset menjadi training dan testing set
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.6, random_state=42)
            loop_update_progress(74, 86)  # Update progress

            # Langkah 6: Inisialisasi model SVM
            model = svm.SVC(kernel='linear')
            loop_update_progress(87, 99)  # Update progress

            # Langkah 7: Melatih model SVM
            model.fit(X_train, y_train)
            update_progress(100, 1)  # Update progress
            update_progress(101, 1)  # Stop progress
            
            status_model = True
            return jsonify({'status_model': status_model})

        except Exception as e:
            print(f'Terjadi kesalahan selama pelatihan model: {str(e)}')
            update_progress(101, 1)  # Stop progress
            update_progress(0)  # Reset progress
            status_model = False
            return jsonify({'status_model': status_model, 'error': str(e)})




# MENJALANKAN APLIKASI FLASK
if __name__ == "__main__":
    app.run(debug=True)

