import os
import mysql.connector
from mysql.connector import Error, pooling
from flask import flash
import bcrypt
import uuid

# Fungsi untuk konfigurasi koneksi database mysql
def create_pool():
    try:
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=5,  # Jumlah maksimum koneksi yang bisa digunakan
            host='localhost',
            database='classification_app',
            user='root',
            password=''
        )
        print("Connection pool berhasil dibuat")
        return connection_pool
    except Error as e:
        print(f"Error saat membuat connection pool: {e}")
        return None

# Fungsi untuk hash password
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

# Fungsi untuk verifikasi password
def verify_password(hashed_password, user_password):
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

# Fungsi untuk memverifikasi login user
def login_user(pool, username, password):
    cursor = None
    connection = None
    try:
        # Ambil koneksi dari pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Eksekusi query untuk mendapatkan user berdasarkan username
        query = "SELECT * FROM tb_pengguna WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if user:
            stored_password = user[2].encode('utf-8')
            if verify_password(stored_password, password):
                return {'status': True, 'id': user[0], 'username': user[1]}
            else:
                flash('Password salah.')
                return {'status': False}
        else:
            flash('Username tidak terdaftar.')
            return {'status': False}

    except mysql.connector.Error as err:
        flash(f'Kesalahan database: {err}')
        return {'status': False}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

# Fungsi untuk registrasi user
def register_user(pool, new_username, new_password):
    cursor = None
    connection = None
    try:
        # Ambil koneksi dari pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Hash password menggunakan bcrypt
        hashed_password = hash_password(new_password)

        # Eksekusi query untuk registrasi pengguna baru
        query = "INSERT INTO tb_pengguna (username, password) VALUES (%s, %s)"
        cursor.execute(query, (new_username, hashed_password))
        connection.commit()

        return {'status': True, 'message': 'Registrasi berhasil. Silakan login.'}

    except mysql.connector.Error as err:
        connection.rollback()
        return {'status': False, 'message': 'Registrasi gagal. Username sudah digunakan.'}
    except Exception as e:
        return {'status': False, 'message': f'Terjadi kesalahan: {str(e)}'}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

# Fungsi untuk generate nama unik gambar
def generate_unique_filename(original_filename, user_id):
    # Ambil ekstensi file
    extension = os.path.splitext(original_filename)[1]
    # Buat nama file unik
    unique_filename = f"{user_id}_{uuid.uuid4().hex}{extension}"
    return unique_filename

# Fungsi untuk menyimpan gambar ke server dan database
def save_classification_result(pool, user_id, filename, unique_filename, max_disease, max_percentage, status):
    cursor = None
    connection = None
    
    try:
        # Ambil koneksi dari pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Simpan hasil klasifikasi ke database
        query = """INSERT INTO classification_results 
                   (user_id, filename, unique_filename, max_disease, max_percentage, status) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (
            user_id,
            filename,
            unique_filename,
            max_disease,
            max_percentage,
            status
        ))
        connection.commit()

    except mysql.connector.Error as err:
        connection.rollback()
        print(f"Error saat menyimpan hasil klasifikasi: {err}")
    except Exception as e:
        print(f'Terjadi kesalahan: {str(e)}')
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

# Fungsi untuk mengambil data hasil klasifikasi dari database
def get_classification_history(pool, user_id, page=1, per_page=10, print=False):
    cursor = None
    connection = None
    results = []
    total_records = 0
    
    try:
        # Ambil koneksi dari pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Pengkondisian berdasarkan parameter 'print'
        if print:
            # Jika print=True, tidak menggunakan LIMIT
            query = """SELECT id, created_at, filename, max_disease, status 
                       FROM classification_results 
                       WHERE user_id = %s 
                       ORDER BY created_at DESC"""
            cursor.execute(query, (user_id,))
        else:
            # Hitung total jumlah data untuk user_id
            count_query = """SELECT COUNT(*) FROM classification_results WHERE user_id = %s"""
            cursor.execute(count_query, (user_id,))
            total_records = cursor.fetchone()[0]  # Ambil nilai total record

            # Hitung offset untuk paginasi
            offset = (page - 1) * per_page
            
            # Jika print=False, menggunakan LIMIT
            query = """SELECT id, created_at, filename, max_disease, status 
                       FROM classification_results 
                       WHERE user_id = %s 
                       ORDER BY created_at DESC 
                       LIMIT %s OFFSET %s"""
            cursor.execute(query, (user_id, per_page, offset))

        # Eksekusi query dan ambil hasilnya
        results = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"Kesalahan database: {err}")
    except Exception as e:
        print(f"Terjadi kesalahan: {str(e)}")
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            
    return results, total_records

# Fungsi untuk menghapus hasil klasifikasi dari database dan file gambar
def delete_classification_result(pool, result_id, user_id, upload_folder):
    connection = None
    cursor = None

    try:
        # Ambil koneksi dari pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Query untuk mendapatkan informasi hasil klasifikasi berdasarkan id dan user_id
        query = "SELECT unique_filename FROM classification_results WHERE id = %s AND user_id = %s"
        cursor.execute(query, (result_id, user_id))
        result = cursor.fetchone()

        if result:
            # Dapatkan nama file unik untuk dihapus dari server
            unique_filename = result[0]
            file_path = os.path.join(upload_folder, unique_filename)

            # Hapus data dari database
            delete_query = "DELETE FROM classification_results WHERE id = %s AND user_id = %s"
            cursor.execute(delete_query, (result_id, user_id))
            connection.commit()
            
            # Hapus file dari server jika ada
            if os.path.exists(file_path):
                os.remove(file_path)

            return True

        return False

    except mysql.connector.Error as err:
        print(f"Kesalahan database: {err}")
        if connection:
            connection.rollback()
        return False

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

# Fungsi untuk menghapus semua hasil klasifikasi
def delete_all_images_by_user(pool, user_id, upload_folder):
    connection = None
    cursor = None

    try:
        # Ambil koneksi dari pool
        connection = pool.get_connection()
        cursor = connection.cursor()

        # Query untuk mendapatkan semua file gambar berdasarkan id_pengguna
        query = "SELECT unique_filename FROM classification_results WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        results = cursor.fetchall()

        if results:
            # Hapus setiap file yang ditemukan
            for result in results:
                unique_filename = result[0]
                file_path = os.path.join(upload_folder, unique_filename)

                # Hapus file dari server jika ada
                if os.path.exists(file_path):
                    os.remove(file_path)

            # Hapus data dari database
            delete_query = "DELETE FROM classification_results WHERE user_id = %s"
            cursor.execute(delete_query, (user_id,))
            connection.commit()

            return True

        return False

    except mysql.connector.Error as err:
        print(f"Kesalahan database: {err}")
        if connection:
            connection.rollback()
        return False

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

