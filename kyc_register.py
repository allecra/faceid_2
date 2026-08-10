# -*- coding: utf-8 -*-
import sys
import os
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from face_matcher import get_insightface_app, get_face_embedding
from cloud_db import save_wallet_vector
from cloud_storage import upload_multiple_images
from ekyc_compliance import verify_full_ekyc_compliance

def register_new_user(user_id, image_input):
    """
    Đăng ký sinh trắc học eKYC Đa Góc Mặt kèm Kiểm tra 5 Quy chuẩn Bảo mật:
    - 1. Môi trường đủ sáng (Brightness > 55)
    - 2. Không nhòe mờ (Blur > 28)
    - 3. Không đeo khẩu trang / Che mặt
    - 4. Không đeo kính mắt
    - 5. Không đội mũ / Phải để lộ rõ trán
    """
    wallet_id = str(user_id).strip()
    print(f"\n--- HỆ THỐNG eKYC BẢO MẬT: ĐĂNG KÝ CHO ID VÍ [{wallet_id}] ---")
    
    frames_list = []
    if isinstance(image_input, list) and len(image_input) > 0:
        frames_list = image_input
    else:
        frames_list = [image_input]

    print(f"[+] Nhận {len(frames_list)} khung hình cử động đa góc mặt từ camera...")

    app = get_insightface_app()

    # 1. Kiểm tra 5 Quy chuẩn eKYC nghiêm ngặt trên khung hình chính diện
    first_frame = frames_list[0]
    faces = app.get(first_frame)
    if not faces:
        print("❌ Đăng ký thất bại: Không tìm thấy khuôn mặt hợp lệ trong khung hình.")
        return False, None, "Không tìm thấy khuôn mặt hợp lệ trong khung hình"

    primary_face = faces[0]
    is_compliant, compliance_msg = verify_full_ekyc_compliance(first_frame, primary_face)
    print(f"[eKYC PRE-CHECK] {compliance_msg}")
    
    if not is_compliant:
        print(f"❌ TỪ CHỐI ĐĂNG KÝ VÌ VI PHẠM QUY CHUẨN: {compliance_msg}")
        return False, None, compliance_msg

    # 2. Trích xuất vectors từ tất cả các khung hình đa góc & tạo 512D Master Vector Ensemble
    vectors_list = []
    for idx, f in enumerate(frames_list):
        vec = get_face_embedding(f)
        if vec is not None:
            norm_val = np.linalg.norm(vec)
            if norm_val > 0:
                vectors_list.append(vec / norm_val)

    if not vectors_list:
        print("❌ Đăng ký thất bại: Không thể mã hóa sinh trắc học.")
        return False, None, "Không thể mã hóa sinh trắc học"

    master_vector = np.mean(vectors_list, axis=0)
    master_vector = master_vector / np.linalg.norm(master_vector)
    print(f"✅ Đã tổng hợp thành công Master Vector 512D Ensemble từ {len(vectors_list)} góc mặt!")

    # 3. Tải toàn bộ mảng 5 ảnh đa góc lên Cloudinary Media Library tài khoản cá nhân
    print(f"☁️ Đang tải {len(frames_list)} ảnh cử động đa góc mặt lên Cloudinary Media Library...")
    cloud_urls = upload_multiple_images(frames_list, folder=f"faceid_ekyc/{wallet_id}")

    # 4. Lưu Master Vector 512D + Cloudinary Image URLs vào Cloud DB
    success = save_wallet_vector(wallet_id, master_vector, image_cloud_url=cloud_urls)
    if success:
        print(f"✅ Đăng ký eKYC thành công! ID Ví [{wallet_id}] đã được lưu trên Cloud DB.")
        return True, cloud_urls, "Đăng ký eKYC thành công!"
    else:
        print("❌ Đăng ký thất bại: Lỗi lưu dữ liệu vào Cloud DB.")
        return False, None, "Lỗi lưu dữ liệu vào Cloud DB"

if __name__ == "__main__":
    WALLET_ID_TEST = "0987654321" 
    IMAGE_REGISTER = os.path.join("img_test", "img_goc.jpg")
    if os.path.exists(IMAGE_REGISTER):
        register_new_user(WALLET_ID_TEST, IMAGE_REGISTER)