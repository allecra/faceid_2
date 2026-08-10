# -*- coding: utf-8 -*-
"""
MODULE CLOUD IMAGE STORAGE DÙNG CLOUDINARY PYTHON SDK CHÍNH THỨC
Tải trực tiếp danh sách mảng 5 ảnh đa góc từ RAM lên Media Library tài khoản Cloudinary cá nhân.
"""
import os
import sys
import json
import base64
import cv2
import numpy as np
# pyrefly: ignore [missing-import]
import cloudinary
# pyrefly: ignore [missing-import]
import cloudinary.uploader
# pyrefly: ignore [missing-import]
import cloudinary.api

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

CONFIG_FILE = "cloudinary_config.json"

def load_cloudinary_config():
    """Tải cấu hình tài khoản Cloudinary cá nhân từ file cloudinary_config.json hoặc Biến môi trường"""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.getenv("CLOUDINARY_API_KEY", "")
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "")

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("cloud_name") and "YOUR_CLOUDINARY" not in cfg["cloud_name"]:
                    cloud_name = cfg.get("cloud_name")
                    api_key = cfg.get("api_key")
                    api_secret = cfg.get("api_secret")
        except Exception as e:
            print(f"[!] Lỗi đọc file {CONFIG_FILE}: {e}")

    if cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        return True, cloud_name
    return False, cloud_name

def upload_single_image(image_input, folder="faceid_ekyc", tags=None):
    """
    Tải 1 khung hình từ RAM lên tài khoản Cloudinary Media Library cá nhân.
    Trả về: URL HTTPS công khai (e.g. https://res.cloudinary.com/your_cloud/image/upload/v.../face.jpg)
    """
    if image_input is None:
        return None

    is_configured, cloud_name = load_cloudinary_config()

    # Chuyển đổi khung hình RAM sang Data URI JPEG
    data_uri = None
    if isinstance(image_input, np.ndarray):
        _, buffer = cv2.imencode('.jpg', image_input)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{img_b64}"
    elif isinstance(image_input, str) and os.path.exists(image_input):
        with open(image_input, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode('utf-8')
            data_uri = f"data:image/jpeg;base64,{img_b64}"
    elif isinstance(image_input, str) and image_input.startswith("data:image"):
        data_uri = image_input

    if not data_uri:
        return None

    if is_configured:
        try:
            res = cloudinary.uploader.upload(
                data_uri,
                folder=folder,
                tags=tags or ["faceid_ekyc"],
                overwrite=True
            )
            cloud_url = res.get("secure_url") or res.get("url")
            print(f"☁️ [CLOUDINARY MEDIA LIBRARY] Đã lưu ảnh lên tài khoản [{cloud_name}]: {cloud_url}")
            return cloud_url
        except Exception as e:
            print(f"[!] Lỗi Cloudinary SDK Upload: {e}")

    # Fallback Demo URL nếu chưa điền API Key cá nhân
    fallback_url = f"https://res.cloudinary.com/demo/image/upload/sample.jpg"
    print(f"☁️ [CLOUDINARY DEMO FALLBACK] URL: {fallback_url}")
    return fallback_url

def upload_multiple_images(image_inputs_list, folder="faceid_ekyc"):
    """
    Tải danh sách mảng 5 ảnh cử động đa góc (Quay trái, Quay phải, Cúi, Ngửa, Chính diện) lên Cloudinary.
    Trả về: Danh sách các đường dẫn HTTPS URLs.
    """
    if not image_inputs_list:
        return []

    urls = []
    poses = ["left_pose", "right_pose", "down_pose", "up_pose", "frontal_pose"]
    
    for idx, img in enumerate(image_inputs_list):
        pose_name = poses[idx] if idx < len(poses) else f"pose_{idx+1}"
        url = upload_single_image(img, folder=folder, tags=["faceid_ekyc", pose_name])
        if url:
            urls.append(url)

    return urls

if __name__ == "__main__":
    test_path = os.path.join("img_test", "img_goc.jpg")
    if os.path.exists(test_path):
        url = upload_single_image(test_path)
        print("Kết quả Cloudinary Upload:", url)
