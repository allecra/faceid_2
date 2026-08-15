# -*- coding: utf-8 -*-
"""
CHƯƠNG TRÌNH XEM TRỰC TIẾP DỮ LIỆU USER_EKYC_BIOMETRICS TỪ POSTGRESQL & SQLITE
"""
import sys
import os
import json
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from cloud_db import get_pg_connection, CLOUD_DB_FILE

def view_all_registered_data():
    print("="*105)
    print("📊 DANH SÁCH DỮ LIỆU SINH TRẮC HỌC BIOMETRICS (POSTGRESQL & SQLITE)")
    print("="*105)

    # 1. Thử xem từ PostgreSQL
    try:
        conn = get_pg_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, ekyc_status, updated_at, image_cloud_urls, face_master_vector, created_by, updated_by 
            FROM user_ekyc_biometrics 
            ORDER BY updated_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if rows:
            print(f"📦 [NGUỒN DỮ LIỆU: POSTGRESQL - BẢNG user_ekyc_biometrics] ({len(rows)} bản ghi)")
            print(f"{'STT':<4} | {'USER ID (UUID)':<38} | {'NGÀY ĐĂNG KÝ':<20} | {'EMAIL / NGƯỜI TẠO':<30} | {'TRẠNG THÁI'}")
            print("-" * 135)
            for idx, row in enumerate(rows, 1):
                u_id, status, updated_at, urls_raw, vec_raw, c_by, u_by = row
                urls = []
                if urls_raw:
                    if isinstance(urls_raw, list): urls = urls_raw
                    elif isinstance(urls_raw, str):
                        try: urls = json.loads(urls_raw)
                        except: urls = [urls_raw]

                print(f"{idx:<4} | {str(u_id):<38} | {str(updated_at)[:19]:<20} | {str(c_by or 'SYSTEM'):<30} | {status}")

                if vec_raw:
                    try:
                        vec = json.loads(vec_raw)
                        print(f"     ├── 🧬 Master Vector 512D Sample: [{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}, {vec[3]:.4f}, ...]")
                    except Exception:
                        pass
                if urls:
                    print(f"     └── ☁️ {len(urls)} URLs ảnh Cloudinary CDN:")
                    for i, u in enumerate(urls, 1):
                        print(f"          [{i}] {u}")
                print("-" * 105)
            return
        else:
            print("ℹ️ Bảng user_ekyc_biometrics trong PostgreSQL hiện chưa có bản ghi nào.")
    except Exception as e:
        print(f"[!] Không kết nối được PostgreSQL: {e}")

    # 2. Xem từ SQLite nếu PostgreSQL chưa có
    if os.path.exists(CLOUD_DB_FILE):
        import sqlite3, pickle
        conn = sqlite3.connect(CLOUD_DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT wallet_id, registered_at, status, vector_blob, image_cloud_url FROM wallet_vectors")
        rows = cursor.fetchall()
        conn.close()

        if rows:
            print(f"\n📦 [NGUỒN DỮ LIỆU DỰ PHÒNG: SQLITE - {CLOUD_DB_FILE}] ({len(rows)} bản ghi)")
            print(f"{'STT':<4} | {'WALLET ID':<38} | {'NGÀY ĐĂNG KÝ':<20} | {'TRẠNG THÁI'}")
            print("-" * 105)
            for idx, row in enumerate(rows, 1):
                w_id, reg_time, status, blob, urls_raw = row
                print(f"{idx:<4} | {w_id:<38} | {reg_time:<20} | {status}")
                try:
                    vec = pickle.loads(blob)
                    print(f"     ├── 🧬 Master Vector 512D Sample: [{vec[0]:.4f}, {vec[1]:.4f}, {vec[2]:.4f}, ...]")
                except Exception:
                    pass
                print("-" * 105)

if __name__ == "__main__":
    view_all_registered_data()
