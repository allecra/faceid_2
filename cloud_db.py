# -*- coding: utf-8 -*-
import os
import sys
import json
import sqlite3
import pickle
import numpy as np
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CLOUD_DB_FILE = "cloud_vector_db.sqlite"

def init_cloud_db():
    """Khởi tạo cấu trúc bảng Cloud Vector & Cloud Image Store"""
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

    cursor.execute("PRAGMA table_info(wallet_vectors)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'image_cloud_url' not in columns:
        cursor.execute("ALTER TABLE wallet_vectors ADD COLUMN image_cloud_url TEXT")
        conn.commit()

    conn.close()
    print(f"[+] Khởi tạo Cloud Database thành công: {CLOUD_DB_FILE}")

init_cloud_db()

def save_wallet_vector(wallet_id, vector_512d, image_cloud_url=None):
    """
    Lưu Vector 512D Master và Danh sách Đường dẫn ảnh Cloudinary CDN của ID Ví vào Cloud Database.
    """
    if wallet_id is None or vector_512d is None:
        print("[!] Lỗi: wallet_id hoặc vector rỗng.")
        return False

    try:
        vec_array = np.array(vector_512d, dtype=np.float32)
        vec_blob = pickle.dumps(vec_array)
        reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Nếu image_cloud_url là danh sách mảng 5 URLs -> Chuyển thành JSON string
        url_str = image_cloud_url
        if isinstance(image_cloud_url, list):
            url_str = json.dumps(image_cloud_url)

        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO wallet_vectors (wallet_id, vector_blob, vector_dim, image_cloud_url, registered_at, status)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            ON CONFLICT(wallet_id) DO UPDATE SET
                vector_blob = excluded.vector_blob,
                image_cloud_url = COALESCE(excluded.image_cloud_url, wallet_vectors.image_cloud_url),
                registered_at = excluded.registered_at
        ''', (str(wallet_id).strip(), vec_blob, len(vec_array), url_str, reg_time))

        conn.commit()
        conn.close()
        print(f"✅ [CLOUD DB] Đã lưu Master Vector 512D + Cloud Image URLs cho ID Ví: [{wallet_id}]")
        return True
    except Exception as e:
        print(f"[!] Lỗi lưu vào Cloud DB: {e}")
        return False

def get_wallet_vector(wallet_id):
    """Truy xuất Master Vector 512D của ID Ví từ Cloud DB"""
    if not wallet_id:
        return None

    try:
        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT vector_blob FROM wallet_vectors WHERE wallet_id = ? AND status = 'ACTIVE'
        ''', (str(wallet_id).strip(),))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return pickle.loads(row[0])
        else:
            return None
    except Exception as e:
        print(f"[!] Lỗi đọc Cloud DB: {e}")
        return None

def list_all_wallets():
    """Liệt kê danh sách tất cả ID Ví, Ngày đăng ký và Danh sách ảnh Cloud CDN"""
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
                if raw_urls.startswith("[") and raw_urls.endswith("]"):
                    try: urls = json.loads(raw_urls)
                    except: urls = [raw_urls]
                else:
                    urls = [raw_urls]

            result.append({
                "wallet_id": w_id,
                "registered_at": r_time,
                "image_cloud_urls": urls
            })

        return result
    except Exception as e:
        print(f"[!] Lỗi liệt kê Cloud DB: {e}")
        return []

if __name__ == "__main__":
    print("Danh sách ID Ví hiện tại:", list_all_wallets())
