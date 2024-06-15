from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
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
custom_message = ''
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

# Route untuk halaman klasifikasi
@app.route('/classification', methods=['GET', 'POST'])
def classification():
    global file_url, file_name, file_path, custom_message, progress
    if request.method == 'POST':
        if 'submit' in request.form:
            file = request.files.get('file')
            if file:
                file_name = file.filename
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
                file.save(file_path)
                file_url = url_for('static', filename=f'uploads/{file_name}')
                progress = 0  # Set progress kembali ke 0
                klasifikasi_gambar_baru()  # Panggil fungsi klasifikasi_gambar_baru untuk memproses gambar
                return render_template('klasifikasi.html', file_url=file_url, file_path=file_path, file_name=file_name, custom_message=custom_message)
        elif 'clear' in request.form:
            file_path = request.form.get('file_path')
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            file_url = ''
            file_name = ''
            custom_message = ''
            progress = 0  # Set progress kembali ke 0
    return render_template('klasifikasi.html', file_url=file_url, file_path='', file_name=file_name, custom_message=custom_message, progress=progress)

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
    global model, progress
    
    if model:
        progress = 101  # Untuk menghentikan fetch dari index.html
        hasil_model = 'Aktif'
        return jsonify({'hasil_model': hasil_model})
    else:
        update_progress(0, 2)  # Update progress
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
        update_progress(101, 1)  # Update progress
        
        hasil_model = 'Aktif'
        return jsonify({'hasil_model': hasil_model})

@app.route('/klasifikasi_gambar_baru')
def klasifikasi_gambar_baru():
    global file_path, custom_message

    # Langkah 8: Klasifikasi gambar baru
    new_image = cv2.imread(file_path)
    prediction = classify_new_image(new_image)
    custom_message = f'{prediction}'

    loop_update_progress(0, 99) # Update progress
        
    update_progress(100, 1)  # Update progress
    update_progress(101, 1)  # Update progress
    return jsonify({'status': 'Task completed!', 'message': custom_message})

if __name__ == "__main__":
    app.run(debug=True)
