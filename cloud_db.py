# -*- coding: utf-8 -*-
"""
MODULE DATABASE BIOMETRICS: HỖ TRỢ POSTGRESQL (CHÍNH) VÀ SQLITE (FALLBACK)
Lưu trữ Master Vector 512D và URLs ảnh Cloudinary vào bảng user_ekyc_biometrics trong PostgreSQL.
"""
import os
import sys
import json
import sqlite3
import pickle
import numpy as np
from datetime import datetime
from urllib.parse import urlparse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─────────────────────────────────────────────────────────────────────────────
# 1. CẤU HÌNH BIẾN MÔI TRƯỜNG & KẾT NỐI POSTGRESQL
# ─────────────────────────────────────────────────────────────────────────────

def load_env_file():
    """Tự động tìm và nạp biến môi trường từ .env của dự án Fintech"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, '.env'),
        os.path.join(current_dir, '..', 'fintech', 'fintech', '.env'),
        os.path.join(current_dir, '..', 'fintech', '.env'),
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k, v = k.strip(), v.strip()
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception as e:
                print(f"[!] Không thể đọc {env_path}: {e}")

load_env_file()

def get_pg_connection():
    """Khởi tạo kết nối PostgreSQL database từ biến môi trường DB_URL"""
    import psycopg2

    db_url = os.getenv('DB_URL', '')
    if db_url.startswith('jdbc:postgresql://'):
        db_url = db_url.replace('jdbc:', '')

    db_user = os.getenv('DB_USERNAME') or 'postgres'
    db_pass = os.getenv('DB_PASSWORD') or 'postgres'

    if db_url:
        parsed = urlparse(db_url)
        return psycopg2.connect(
            dbname=parsed.path.lstrip('/') or 'postgres',
            user=db_user if db_user != 'postgres' else (parsed.username or 'postgres'),
            password=db_pass if db_pass != 'postgres' else (parsed.password or 'postgres'),
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            connect_timeout=5
        )
    else:
        return psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'postgres'),
            user=db_user,
            password=db_pass,
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            connect_timeout=5
        )

# ─────────────────────────────────────────────────────────────────────────────
# 2. LOCAL SQLITE FALLBACK SETUP
# ─────────────────────────────────────────────────────────────────────────────

CLOUD_DB_FILE = "cloud_vector_db.sqlite"

def init_sqlite_db():
    """Khởi tạo SQLite dự phòng nếu chưa có PostgreSQL"""
    try:
        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_vectors (
                wallet_id TEXT PRIMARY KEY,
                vector_blob BLOB NOT NULL,
                vector_dim INTEGER NOT NULL,
                image_cloud_url TEXT,
                registered_at TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE'
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] Lỗi khởi tạo SQLite: {e}")

init_sqlite_db()

# ─────────────────────────────────────────────────────────────────────────────
# 3. LƯU MASTER VECTOR 512D (POSTGRESQL CHÍNH + SQLITE DỰ PHÒNG)
# ─────────────────────────────────────────────────────────────────────────────

def save_wallet_vector(wallet_id, vector_512d, image_cloud_url=None):
    """
    Lưu Vector 512D Master và Danh sách URLs ảnh Cloudinary vào bảng user_ekyc_biometrics (PostgreSQL).
    """
    if wallet_id is None or vector_512d is None:
        print("[!] Lỗi: wallet_id hoặc vector rỗng.")
        return False

    user_id_str = str(wallet_id).strip()
    vec_array = np.array(vector_512d, dtype=np.float32)
    vec_json = json.dumps(vec_array.tolist())

    url_json = None
    if isinstance(image_cloud_url, list):
        url_json = json.dumps(image_cloud_url)
    elif isinstance(image_cloud_url, str):
        url_json = image_cloud_url if image_cloud_url.startswith('[') else json.dumps([image_cloud_url])

    saved_to_pg = False

    # 1. Lưu vào PostgreSQL database (user_ekyc_biometrics)
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()

        # Truy vấn email của user từ bảng users để ghi nhận created_by / updated_by
        user_email = None
        try:
            cursor.execute("SELECT email FROM users WHERE id::text = %s", (user_id_str,))
            u_row = cursor.fetchone()
            if u_row and u_row[0]:
                user_email = str(u_row[0]).strip()
        except Exception as query_err:
            print(f"[!] Không tìm thấy email của user {user_id_str}: {query_err}")

        actor = user_email if user_email else user_id_str

        cursor.execute('''
            INSERT INTO user_ekyc_biometrics (
                user_id, face_master_vector, ekyc_status, image_cloud_urls, 
                created_at, updated_at, created_by, updated_by
            )
            VALUES (%s, %s, 'COMPLIANT_PASSED', %s, NOW(), NOW(), %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                face_master_vector = EXCLUDED.face_master_vector,
                ekyc_status = 'COMPLIANT_PASSED',
                image_cloud_urls = COALESCE(EXCLUDED.image_cloud_urls, user_ekyc_biometrics.image_cloud_urls),
                updated_at = NOW(),
                updated_by = EXCLUDED.updated_by;
        ''', (user_id_str, vec_json, url_json, actor, actor))
        conn.commit()


        cursor.close()
        conn.close()
        print(f"✅ [POSTGRESQL DB] Đã lưu Master Vector 512D vào bảng user_ekyc_biometrics cho user: [{user_id_str}]")
        saved_to_pg = True
    except Exception as e:
        print(f"[!] Không thể lưu vào PostgreSQL user_ekyc_biometrics: {e}")

    # 2. Đồng thời lưu vào SQLite local làm cache/backup
    try:
        vec_blob = pickle.dumps(vec_array)
        reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO wallet_vectors (wallet_id, vector_blob, vector_dim, image_cloud_url, registered_at, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            ON CONFLICT(wallet_id) DO UPDATE SET
                vector_blob = excluded.vector_blob,
                image_cloud_url = COALESCE(excluded.image_cloud_url, wallet_vectors.image_cloud_url),
                registered_at = excluded.registered_at
        ''', (user_id_str, vec_blob, len(vec_array), url_json, reg_time))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[!] Lỗi ghi backup SQLite: {e}")

    return saved_to_pg or True

# ─────────────────────────────────────────────────────────────────────────────
# 4. TRUY XUẤT MASTER VECTOR 512D
# ─────────────────────────────────────────────────────────────────────────────

def get_wallet_vector(wallet_id):
    """
    Truy xuất Master Vector 512D của user: Ưu tiên đọc từ PostgreSQL, fallback sang SQLite.
    """
    if not wallet_id:
        return None

    user_id_str = str(wallet_id).strip()

    # 1. Đọc từ PostgreSQL (user_ekyc_biometrics)
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT face_master_vector 
            FROM user_ekyc_biometrics 
            WHERE user_id::text = %s 
              AND ekyc_status = 'COMPLIANT_PASSED'
        ''', (user_id_str,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row and row[0]:
            vec_list = json.loads(row[0])
            print(f"🔍 [POSTGRESQL DB] Đã nạp Master Vector 512D từ user_ekyc_biometrics cho user [{user_id_str}]")
            return np.array(vec_list, dtype=np.float32)
    except Exception as e:
        print(f"[!] Không đọc được từ PostgreSQL: {e}. Thử fallback sang SQLite...")

    # 2. Fallback sang SQLite
    try:
        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT vector_blob FROM wallet_vectors WHERE wallet_id = ? AND status = 'ACTIVE'
        ''', (user_id_str,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            print(f"🔍 [SQLITE BACKUP] Đã nạp Master Vector 512D từ SQLite cho user [{user_id_str}]")
            return pickle.loads(row[0])
    except Exception as e:
        print(f"[!] Lỗi đọc SQLite: {e}")

    return None

# ─────────────────────────────────────────────────────────────────────────────
# 5. LIỆT KÊ DANH SÁCH USER ĐÃ ĐĂNG KÝ
# ─────────────────────────────────────────────────────────────────────────────

def list_all_wallets():
    """Liệt kê danh sách tất cả ID Ví, Ngày đăng ký và Danh sách ảnh Cloud CDN"""
    # 1. Thử từ PostgreSQL
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, updated_at, image_cloud_urls, ekyc_status 
            FROM user_ekyc_biometrics 
            ORDER BY updated_at DESC
        ''')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for r in rows:
            u_id, r_time, raw_urls, status = r[0], r[1], r[2], r[3]
            urls = []
            if raw_urls:
                if isinstance(raw_urls, list):
                    urls = raw_urls
                elif isinstance(raw_urls, str):
                    try: urls = json.loads(raw_urls)
                    except: urls = [raw_urls]

            result.append({
                "wallet_id": str(u_id),
                "registered_at": str(r_time),
                "image_cloud_urls": urls,
                "status": status,
                "source": "POSTGRESQL"
            })
        if result:
            return result
    except Exception as e:
        print(f"[!] Lỗi đọc danh sách từ PostgreSQL: {e}")

    # 2. Fallback sang SQLite
    try:
        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT wallet_id, registered_at, image_cloud_url FROM wallet_vectors')
        rows = cursor.fetchall()
        conn.close()

        result = []
        for r in rows:
            w_id, r_time, raw_urls = r[0], r[1], r[2]
            urls = []
            if raw_urls:
                try: urls = json.loads(raw_urls)
                except: urls = [raw_urls]

            result.append({
                "wallet_id": w_id,
                "registered_at": r_time,
                "image_cloud_urls": urls,
                "status": "ACTIVE",
                "source": "SQLITE"
            })
        return result
    except Exception as e:
        print(f"[!] Lỗi liệt kê SQLite: {e}")
        return []

if __name__ == "__main__":
    print("Danh sách Biometrics hiện tại:", list_all_wallets())
