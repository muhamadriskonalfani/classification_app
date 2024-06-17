from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import mysql.connector
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
from skimage.feature import hog
from sklearn import svm
from sklearn.model_selection import train_test_split
import time

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'static/uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

file_url = ''
file_name = ''
file_path = ''
prediction = ''
model = ''
progress = 0  # Menyimpan progress

# Konfigurasi koneksi database MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="classification_app"
)

# Route untuk halaman utama/index
@app.route('/')
def index():
    return render_template('index.html')

# Route untuk halaman utama/index
@app.route('/training_model')
def training_model():
    return render_template('training_model.html')

# Route untuk halaman klasifikasi
@app.route('/classification', methods=['GET', 'POST'])
def classification():
    global progress
    
    progress = 0  # Set progress kembali ke 0
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tb_gambar ORDER BY id_gambar DESC")
    items = cursor.fetchall()
    
    cursor.execute("SELECT * FROM tb_gambar ORDER BY id_gambar DESC LIMIT 1")
    latest = cursor.fetchone()
    
    return render_template('classification.html', items=items, latest=latest)


# Route untuk menambah item
@app.route('/add_to_database', methods=['GET', 'POST'])
def add_to_database():
    global file_url, file_name, file_path, prediction
    
    if request.method == 'POST':
        if 'submit' in request.form:
            file = request.files.get('file')
            if file:
                file_name = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                file.save(file_path)
                file_url = url_for('static', filename=f'uploads/{file_name}')
                klasifikasi_gambar_baru() 
    
    cursor = db.cursor()
    cursor.execute("INSERT INTO tb_gambar (gambar, status) VALUES (%s, %s)", (file_name, prediction))
    db.commit()
    
    return redirect('/classification')

# Route untuk menghapus item
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_from_database(item_id):
    cursor = db.cursor()
    cursor.execute("SELECT gambar FROM tb_gambar WHERE id_gambar = %s", (item_id,))
    image = cursor.fetchone()[0]
    if image:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image))
    cursor.execute("DELETE FROM tb_gambar WHERE id_gambar = %s", (item_id,))
    db.commit()
    
    return redirect('/classification')


# Endpoint untuk melayani file statis
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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

def update_progress(val, delay=0):
    global progress
    progress = val
    time.sleep(delay)
    
def loop_update_progress(start, end):
    for step in range(start, end):
        time.sleep(0.05)
        update_progress(step)

@app.route('/progress')
def progress_status():
    global progress
    return jsonify({'progress': progress})

@app.route('/latih_model_klasifikasi')
def latih_model_klasifikasi():
    global model
    
    update_progress(0, 1)  # Start progress
    loop_update_progress(1, 14) # Update progress
    
    # Langkah 1: Memuat dataset dari folder lokal
    folder_path = './rice_leaf_diseases'
    images, labels = load_images_from_folder(folder_path)
    loop_update_progress(15, 27) # Update progress

    # Langkah 2: Pra-pemrosesan setiap gambar
    preprocessed_images = [preprocess_image(cv2.resize(image, (384, 128))) for image in images]
    loop_update_progress(28, 37) # Update progress

    # Langkah 3: Ekstraksi fitur HOG untuk setiap gambar yang sudah dipra-pemrosesan
    features = [extract_hog_features(image) for image in preprocessed_images]
    loop_update_progress(48, 60) # Update progress

    # Langkah 4: Menyatukan fitur HOG menjadi satu array homogen
    X = np.array(features)
    y = np.array(labels)
    loop_update_progress(61, 73) # Update progress

    # Langkah 5: Membagi dataset menjadi training dan testing set
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.6, random_state=42)
    loop_update_progress(74, 86) # Update progress

    # Langkah 6: Inisialisasi model SVM
    model = svm.SVC(kernel='linear')
    loop_update_progress(87, 99) # Update progress

    # Langkah 7: Melatih model SVM
    model.fit(X_train, y_train)
    update_progress(100, 1)  # Update progress
    update_progress(101, 1)  # Stop progress
    
    hasil_model = 'Aktif'
    return jsonify({'hasil_model': hasil_model})

def klasifikasi_gambar_baru():
    global file_path, prediction
    
    update_progress(0, 1)  # Start progress

    # Langkah 8: Klasifikasi gambar baru
    new_image = cv2.imread(file_path)
    prediction = classify_new_image(new_image)

    loop_update_progress(1, 99) # Update progress
    update_progress(100, 1)  # Update progress
    update_progress(101, 1)  # Stop progress

if __name__ == "__main__":
    app.run(debug=True)

