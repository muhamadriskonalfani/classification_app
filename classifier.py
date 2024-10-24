import os
import cv2
import numpy as np
from skimage.feature import hog
from skimage import exposure
from sklearn import svm
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import json
from utils import preprocess_image, extract_hog_features, load_images_from_folder, extract_color_features, extract_texture_features

evaluation_filename = 'models/model_evaluation.json'

# Fungsi untuk mengecek status penyakit
def check_if_known_disease(max_percentage):
    return "Unknown" if max_percentage <= 0 or max_percentage >= 100 else ""

# Fungsi klasifikasi untuk gambar baru
def classify_new_image(image_path, model):
    # Baca gambar
    image = cv2.imread(image_path)
    
    # Pra-pemrosesan gambar
    preprocessed_image = preprocess_image(image)
    
    # Ekstraksi fitur HOG, warna, dan tekstur
    hog_features, _ = extract_hog_features(preprocessed_image)
    color_features = extract_color_features(image)
    texture_features = extract_texture_features(preprocessed_image)
    
    # Gabungkan fitur menjadi satu array dan ubah ke bentuk 1D
    combined_features = np.hstack([hog_features.flatten(), color_features, texture_features]).reshape(1, -1)
    
    # Prediksi menggunakan model
    probabilities = model.predict_proba(combined_features)
    
    # Menggabungkan hasil prediksi dengan nama kelas
    prediction_results = {}
    class_names = model.classes_
    for class_name, prob in zip(class_names, probabilities[0]):
        prediction_results[class_name] = prob * 100
    
    # Cari penyakit dengan probabilitas tertinggi
    max_disease = max(prediction_results, key=prediction_results.get)
    max_percentage = prediction_results[max_disease]
    
    # Cek status penyakit
    status = check_if_known_disease(max_percentage)
    
    return max_disease, max_percentage, status

# Fungsi untuk memuat atau membuat model jika belum ada
def load_or_train_model(model_filename):
    if os.path.exists(model_filename) and os.path.getsize(model_filename) > 0:
        print(f"Model ditemukan dan valid. Memuat model dari {model_filename}...")
        return joblib.load(model_filename)
    else:
        print("Model belum ditemukan atau file tidak valid. Melakukan pelatihan model...")
        # Load dataset (untuk pelatihan pertama kali)
        folder_path = 'static/rice_leaf_diseases_2'
        images, labels = load_images_from_folder(folder_path)
        
        # Pra-pemrosesan setiap gambar dan ekstraksi fitur
        features = []
        for image in images:
            preprocessed_image = preprocess_image(image)
            hog_features, _ = extract_hog_features(preprocessed_image)
            color_features = extract_color_features(image)
            texture_features = extract_texture_features(preprocessed_image)
            combined_features = np.hstack([hog_features, color_features, texture_features])
            features.append(combined_features)

        # Menyatukan fitur menjadi satu array homogen
        X = np.array(features)
        y = np.array(labels)

        # Membagi dataset menjadi training dan testing set
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Inisialisasi model SVM dengan probabilitas
        svm_model = svm.SVC(probability=True)

        # Menyediakan parameter untuk GridSearchCV
        param_grid = {
            'C': [1, 10],         
            'kernel': ['linear', 'rbf', 'poly'],
            'gamma': ['scale', 'auto'],        
        }

        # Stratified K-Fold Cross-Validation
        stratified_kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        # GridSearchCV
        grid_search = GridSearchCV(svm_model, param_grid, cv=stratified_kfold, scoring='accuracy', verbose=2, n_jobs=-1)

        # Melatih model
        grid_search.fit(X_train, y_train)

        # Mendapatkan hyperparameters terbaik
        print(f"Best parameters found: {grid_search.best_params_}")

        # Simpan model terbaik
        best_model = grid_search.best_estimator_
        joblib.dump(best_model, model_filename)

        # Evaluasi model
        y_pred = best_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted')
        recall = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')

        # Simpan hasil evaluasi
        evaluation_results = {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1_score': f1}
        with open(evaluation_filename, 'w') as eval_file:
            json.dump(evaluation_results, eval_file)

        print(f"Model telah disimpan ke {model_filename} dan evaluasi disimpan ke {evaluation_filename}")
        return best_model

