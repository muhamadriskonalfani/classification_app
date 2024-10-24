from flask import Flask, request, render_template, redirect, url_for, jsonify, flash, session
import os
import json
from classifier import load_or_train_model, classify_new_image, evaluation_filename
from utils import is_model_valid, model_required
import mysql.connector
from database import create_pool, login_user, register_user, generate_unique_filename, save_classification_result, get_classification_history, delete_classification_result, delete_all_images_by_user




# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_FOLDER'] = 'static/uploads'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
model_filename = 'models/svm_rice_leaf_model.pkl'
pool = create_pool() # buat connection pool database




# Route untuk halaman utama
@app.route('/')
def index():
    username = None
    
    if 'username' in session:
        username = session['username']
    
    return render_template('main/index.html', username=username)

# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Gunakan fungsi login_user untuk memverifikasi login
        result = login_user(pool, username, password)

        if result['status']:  # Jika login berhasil
            # Hapus semua session
            session.clear()

            # Simpan sesi pengguna yang baru login
            session['id_pengguna'] = result['id']
            session['username'] = result['username']
            return redirect(url_for('index'))
        else:
            flash('Login gagal. Silakan coba lagi.')

    return render_template('auth/login.html')

# Route untuk registrasi
@app.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']

        # Panggil fungsi register_user dari database.py
        result = register_user(pool, new_username, new_password)

        if result['status']:
            flash(result['message'])
            return redirect(url_for('login'))
        else:
            flash(result['message'])

    return render_template('auth/daftar.html')

# Route untuk logout
@app.route('/logout')
def logout():
    # Hapus semua session
    session.clear()
    flash('Anda telah logout.')
        
    return redirect(url_for('index'))

# Route untuk halaman klasifikasi
@app.route('/classification')
@model_required(model_filename)
def classification():
    return render_template('main/classification.html')

# Route untuk halaman hasil klasifikasi
@app.route('/result')
@model_required(model_filename)
def result():
    # Mengambil dictionary dari session
    all_results = session.get('all_results', None)
    disease_count = session.get('disease_count', None)
    
    return render_template('main/result.html', all_results=all_results, disease_count=disease_count)

# Route untuk halaman histori dengan paginasi
@app.route('/histori', methods=['GET'])
@model_required(model_filename)
def histori():
    try:
        # Pastikan pengguna sudah login
        user_id = session.get('id_pengguna')
        username = session.get('username')
        if user_id is None or username is None:
            flash('Silakan login terlebih dahulu.')
            return redirect(url_for('login'))
        
        # Ambil parameter 'page' dan 'per_page' dari query string
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Mengambil data histori klasifikasi berdasarkan user_id dengan paginasi
        history_data, total_records = get_classification_history(pool, user_id, page=page, per_page=per_page)

        # Hitung total halaman
        total_pages = (total_records + per_page - 1) // per_page

        # Batasi tampilan pagination maksimal 5 halaman
        pagination_range = 5
        start_page = max(1, page - (pagination_range // 2))
        end_page = min(total_pages, start_page + pagination_range - 1)

        # Adjust if the total pages are less than pagination_range
        if end_page - start_page + 1 < pagination_range:
            start_page = max(1, end_page - pagination_range + 1)

        # Format data untuk ditampilkan di tabel
        formatted_history = []
        for i, record in enumerate(history_data, start=(page-1)*per_page + 1):  # Update start number sesuai dengan paginasi
            formatted_history.append({
                'no': i,
                'tanggal': record[1].strftime('%d %B %Y'),
                'nama_file': record[2],
                'hasil_klasifikasi': record[3],
                'status': record[4],
                'id': record[0]
            })

    except Exception as e:
        print(f'Terjadi kesalahan: {str(e)}')
        formatted_history = []

    return render_template('main/histori.html', username=username, history_data=formatted_history, page=page, total_pages=total_pages, per_page=per_page, start_page=start_page, end_page=end_page)

# Route untuk cetak laporan klasifikasi
@app.route('/cetak_laporan')
@model_required(model_filename)
def cetak_laporan():
    try:
        # Pastikan pengguna sudah login
        user_id = session.get('id_pengguna')
        if user_id is None:
            flash('Silakan login terlebih dahulu.')
            return redirect(url_for('login'))

        # Mengambil data histori klasifikasi berdasarkan id_pengguna
        history_data, _ = get_classification_history(pool, user_id, print=True)

        # Format data untuk ditampilkan di tabel
        formatted_history = []
        for i, record in enumerate(history_data, start=1):
            formatted_history.append({
                'no': i,
                'tanggal': record[1].strftime('%d %B %Y'),
                'nama_file': record[2],
                'hasil_klasifikasi': record[3],
                'status': record[4],
                'id': record[0]
            })

    except Exception as e:
        print(f'Terjadi kesalahan: {str(e)}')
        history_data = []

    return render_template('main/cetak_laporan.html', history_data=formatted_history)

# Route untuk halaman bantuan
@app.route('/bantuan')
@model_required(model_filename)
def bantuan():
    return render_template('main/bantuan.html')

# Route untuk halaman informasi penyakit
@app.route('/informasi_penyakit')
@model_required(model_filename)
def informasi_penyakit():
    return render_template('main/informasi_penyakit.html')

# Route untuk halaman informasi model
@app.route('/informasi_model')
@model_required(model_filename)
def informasi_model():
    # Membaca data dari file JSON
    if os.path.exists(evaluation_filename):
        with open('models/model_evaluation.json') as f:
            evaluation_metrics = json.load(f)
    else:
        evaluation_metrics = None
    
    return render_template('main/informasi_model.html', metrics=evaluation_metrics)




# Route untuk membuat model klasifikasi
@app.route('/train_model', methods=['POST'])
def train_model():
    try:
        # Load model (atau latih jika belum ada)
        model = load_or_train_model(model_filename)
        
        # Jika model berhasil dibuat atau diload, arahkan ke halaman klasifikasi
        if model:
            return jsonify({'status': 'success', 'redirect': url_for('classification')})
        
        # Jika model tidak berhasil, render halaman index dengan pesan kesalahan
        return jsonify({'status': 'failed', 'message': 'Gagal membuat atau memuat model'})
    
    except Exception as e:
        # Jika ada kesalahan lain, kembalikan respons dengan error
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Route untuk mengunggah, memproses banyak gambar, dan menyimpan hasil klasifikasinya
@app.route('/upload', methods=['POST'])
@model_required(model_filename)
def upload_image():
    if 'file' not in request.files:
        flash('Tidak ada file yang diunggah.')
        return redirect(request.url)
    
    files = request.files.getlist('file')  # Mengambil semua file yang diunggah
    user_id = session.get('id_pengguna')  # Ambil ID pengguna dari session
    
    if not files or not user_id:
        flash('Terjadi kesalahan. Pastikan Anda telah login dan file yang diunggah valid.')
        return redirect(request.url)
    
    # Load model sekali untuk semua file
    model = load_or_train_model(model_filename)
    
    all_results = []
    disease_count = {'total': 0, 'Bacterial leaf blight': 0, 'Brown spot': 0, 'Leaf smut': 0}
    
    for file in files:
        if file.filename == '':
            continue
        
        # Generate nama file unik
        unique_filename = generate_unique_filename(file.filename, user_id)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        filepath = filepath.replace('\\', '/')  # Replace backslashes with forward slashes
        file.save(filepath)

        # Klasifikasikan setiap gambar yang diunggah
        max_disease, max_percentage, status = classify_new_image(filepath, model)

        # Simpan hasil klasifikasi ke database
        save_classification_result(pool, user_id, filename=file.filename, unique_filename=unique_filename, max_disease=max_disease, max_percentage=max_percentage, status=status)
        
        # Simpan hasil prediksi dan informasi lainnya untuk ditampilkan
        all_results.append({
            'filename': file.filename,
            'max_disease': max_disease,
            'max_percentage': max_percentage,
            'status': status,
            'image_url': filepath
        })
        
        # Update total input dan perhitungan penyakit
        disease_count['total'] += 1
        if max_disease in disease_count:
            disease_count[max_disease] += 1
        
        # Simpan dictionary ke dalam session
        session['all_results'] = all_results
        session['disease_count'] = disease_count
    
    # Render halaman hasil dengan menampilkan semua hasil klasifikasi
    return render_template('main/result.html', all_results=all_results, disease_count=disease_count)

# Route untuk menghapus model klasifikasi
@app.route('/delete_model_files', methods=['DELETE'])
@model_required(model_filename)
def delete_model_files():
    # Daftar file yang akan dihapus
    files_to_delete = [
        'models/model_evaluation.json',
        'models/svm_rice_leaf_model.pkl'
    ]
    
    deleted_files = []
    errors = []

    # Menghapus setiap file dalam daftar
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_files.append(file_path)
            else:
                errors.append(f'File tidak ditemukan: {file_path}')
        except Exception as e:
            errors.append(f'Error saat menghapus {file_path}: {str(e)}')

    # Mengembalikan respons
    return jsonify({
        'deleted_files': deleted_files,
        'errors': errors
    }), 200

# Endpoint untuk menghapus hasil klasifikasi
@app.route('/delete_result/<int:id>', methods=['POST'])
def delete_result(id):
    user_id = session.get('id_pengguna')

    if user_id is None:
        flash("Anda harus login untuk menghapus hasil.")
        return redirect(url_for('login'))

    # Panggil fungsi untuk menghapus hasil dari database dan file dari server
    success = delete_classification_result(pool, id, user_id, app.config['UPLOAD_FOLDER'])

    if not success:
        flash("Gagal menghapus hasil klasifikasi.")

    return redirect(url_for('histori'))

# Endpoint untuk menghapus semua hasil klasifikasi
@app.route('/delete_all_images', methods=['GET', 'POST'])
def delete_all_images():
    user_id = session.get('id_pengguna')

    if user_id is None:
        flash("Anda harus login untuk menghapus semua gambar.")
        return redirect(url_for('login'))

    # Panggil fungsi untuk menghapus semua gambar dari database dan file dari server
    success = delete_all_images_by_user(pool, user_id, app.config['UPLOAD_FOLDER'])

    if not success:
        flash("Gagal menghapus semua gambar.")

    return redirect(url_for('histori'))






if __name__ == "__main__":
    app.run(debug=True)

