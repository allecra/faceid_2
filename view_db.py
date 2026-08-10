# -*- coding: utf-8 -*-
"""
CHƯƠNG TRÌNH XEM TRỰC TIẾP DỮ LIỆU CLOUD VECTOR DATABASE & CLOUDINARY MEDIA LIBRARY URLS
"""
import sys
import os
import json
import sqlite3
import pickle
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CLOUD_DB_FILE = "cloud_vector_db.sqlite"

def view_all_registered_data():
    if not os.path.exists(CLOUD_DB_FILE):
        print(f"[!] File cơ sở dữ liệu {CLOUD_DB_FILE} chưa được tạo. Hãy chạy ứng dụng và đăng ký eKYC trước!")
        return

    conn = sqlite3.connect(CLOUD_DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(wallet_vectors)")
    cols = [col[1] for col in cursor.fetchall()]
    
    if 'image_cloud_url' in cols:
        cursor.execute("SELECT wallet_id, vector_dim, registered_at, status, vector_blob, image_cloud_url FROM wallet_vectors")
    else:
        cursor.execute("SELECT wallet_id, vector_dim, registered_at, status, vector_blob, NULL FROM wallet_vectors")

    rows = cursor.fetchall()
    conn.close()

    print("="*100)
    print(f"📊 DANH SÁCH DỮ LIỆU TRONG CLOUD VECTOR DATABASE ({CLOUD_DB_FILE})")
    print("="*100)

    if not rows:
        print("Chưa có dữ liệu ID Ví nào được đăng ký.")
        return

    print(f"{'STT':<4} | {'ID VÍ / SĐT KHÁCH HÀNG':<22} | {'NGÀY ĐĂNG KÝ':<20} | {'SỐ ẢNH CLOUD'}")
    print("-" * 100)

    for idx, row in enumerate(rows, 1):
        wallet_id, dim, reg_time, status, blob, cloud_url_raw = row
        urls = []
        if cloud_url_raw:
            if cloud_url_raw.startswith("[") and cloud_url_raw.endswith("]"):
                try: urls = json.loads(cloud_url_raw)
                except: urls = [cloud_url_raw]
            else:
                urls = [cloud_url_raw]

        print(f"{idx:<4} | {wallet_id:<22} | {reg_time:<20} | {len(urls)} ảnh trên Cloudinary")
        
        try:
            vec_array = pickle.loads(blob)
            print(f"     ├── 🧬 Master Vector 512D Sample: [{vec_array[0]:.4f}, {vec_array[1]:.4f}, {vec_array[2]:.4f}, {vec_array[3]:.4f}, {vec_array[4]:.4f}, ...]")
        except Exception:
            pass

        if urls:
            print("     └── ☁️ Danh sách Ảnh trên Cloudinary Media Library cá nhân:")
            for i, u in enumerate(urls, 1):
                print(f"          [{i}] {u}")
        else:
            print("     └── ☁️ Chưa có Cloudinary Image URL (Hãy điền cloudinary_config.json)")
        print("-" * 100)

if __name__ == "__main__":
    view_all_registered_data()
