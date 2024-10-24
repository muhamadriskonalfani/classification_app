import os
import cv2
import numpy as np
from skimage.feature import hog, local_binary_pattern
from skimage import exposure
from functools import wraps
from flask import redirect, url_for, flash, session
import joblib

# Fungsi dekorator untuk validasi model
def model_required(model_path):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Cek apakah model ada
            if not os.path.exists(model_path):
                return redirect(url_for('index'))

            # Cek apakah sudah login
            if 'id_pengguna' not in session and 'username' not in session:
                flash("Anda harus login terlebih dahulu.", "warning")
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Fungsi untuk memeriksa apakah file model valid
def is_model_valid(filepath):
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            joblib.load(filepath)
            return True
        except:
            return False
    return False

# Fungsi untuk memuat dan melabeli gambar dari folder
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

# Fungsi untuk pra-pemrosesan gambar dengan padding
def preprocess_image(image, target_size=(256, 256)):
    original_size = image.shape[:2]
    ratio = min(target_size[0] / original_size[0], target_size[1] / original_size[1])
    new_size = (int(original_size[1] * ratio), int(original_size[0] * ratio))
    resized_img = cv2.resize(image, new_size)

    padded_img = np.zeros((target_size[0], target_size[1], 3), dtype=np.uint8)
    pad_top = (target_size[0] - new_size[1]) // 2
    pad_left = (target_size[1] - new_size[0]) // 2
    padded_img[pad_top:pad_top + new_size[1], pad_left:pad_left + new_size[0], :] = resized_img

    gray_img = cv2.cvtColor(padded_img, cv2.COLOR_BGR2GRAY)
    enhanced_img = cv2.equalizeHist(gray_img)
    denoised_img = cv2.GaussianBlur(enhanced_img, (5, 5), 0)
    return denoised_img

# Fungsi untuk mengekstraksi fitur HOG
def extract_hog_features(image):
    features, hog_image = hog(image, pixels_per_cell=(16, 16), cells_per_block=(2, 2), visualize=True)
    hog_image_rescaled = exposure.rescale_intensity(hog_image, in_range=(0, 10))
    return features, hog_image_rescaled

# Fungsi untuk mengekstraksi fitur warna
def extract_color_features(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h_hist = cv2.calcHist([hsv_image], [0], None, [256], [0, 256])
    s_hist = cv2.calcHist([hsv_image], [1], None, [256], [0, 256])
    v_hist = cv2.calcHist([hsv_image], [2], None, [256], [0, 256])
    color_features = np.hstack([h_hist.flatten(), s_hist.flatten(), v_hist.flatten()])
    return color_features

# Fungsi untuk mengekstraksi fitur tekstur menggunakan LBP
def extract_texture_features(image):
    radius = 3
    n_points = 8 * radius
    lbp = local_binary_pattern(image, n_points, radius, method='uniform')
    (lbp_hist, _) = np.histogram(lbp.ravel(), bins=np.arange(0, n_points + 3), range=(0, n_points + 2))
    lbp_hist = lbp_hist.astype("float")
    lbp_hist /= (lbp_hist.sum() + 1e-6)
    return lbp_hist

