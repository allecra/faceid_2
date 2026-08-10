# -*- coding: utf-8 -*-
import sys
import os
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from liveness_check import verify_liveness, verify_liveness_multi_frame
from face_matcher import get_face_embedding, compute_cosine_similarity
from cloud_db import get_wallet_vector

# Ngưỡng an toàn sản xuất cho InsightFace ArcFace (buffalo_l): 0.40
THRESHOLD = 0.40

def get_vector_from_db(user_id):
    """Tìm vector sinh trắc học 512D Master của ID Ví trong Cloud DB  """
    return get_wallet_vector(user_id)

def verify_transaction(user_id, image_input, active_liveness_passed=False):
    """
    Xác thực giao dịch 2 trạm (Anti-Spoofing & Cloud DB Match):
    - user_id: ID Ví người chuyển tiền (Wallet ID / SĐT)
    - image_input: filepath (str), khung hình đơn (np.ndarray), hoặc mảng danh sách khung hình. 
    """
    wallet_id = str(user_id).strip()
    print("="*60)
    print(f"XÁC THỰC GIAO DỊCH TÀI CHÍNH CHO ID VÍ: [{wallet_id}]")
    print("="*60)
    
    # 0. Lấy vector Master 512D của ID Ví từ Cloud DB
    vector_db = get_vector_from_db(wallet_id)
    if vector_db is None: 
        print(f"❌ TỪ CHỐI GIAO DỊCH: ID Ví [{wallet_id}] chưa đăng ký sinh trắc học (eKYC) trên Cloud DB.")
        return False

    # --- TRẠM 1: ANTI-SPOOFING (LIVENESS) ---
    print("\n[Trạm 1] Kiểm tra Liveness (Anti-Spoofing MiniFASNet)...")
    
    is_live = False
    representative_frame = None

    if isinstance(image_input, list) and len(image_input) > 0:
        is_live = verify_liveness_multi_frame(image_input, active_liveness_passed=active_liveness_passed)
        representative_frame = image_input[-1]
    else:
        is_live = verify_liveness(image_input, active_liveness_passed=active_liveness_passed)
        representative_frame = image_input

    if not is_live:
        print("❌ TỪ CHỐI GIAO DỊCH: Phát hiện ảnh in / màn hình máy tính mạo danh ở Trạm 1. !")
        return False
        
    print("✅ VƯỢT QUA TRẠM 1 (Khuôn mặt thật đạt chuẩn Liveness).")

    # --- TRẠM 2: SO KHỚP VECTOR SINH TRẮC HỌC 512D ---
    print("\n[Trạm 2] Đối chiếu vector sinh trắc học 512D với Cloud DB...")

    vector_camera = get_face_embedding(representative_frame)
    if vector_camera is None:
        print("❌ TỪ CHỐI: Không trích xuất được đặc trưng khuôn mặt từ camera.")
        return False

    # Chuẩn hóa L2 Norm 2 vector trước khi tính Cosine Similarity
    v1 = np.array(vector_db, dtype=np.float32)
    v2 = np.array(vector_camera, dtype=np.float32)
    
    if np.linalg.norm(v1) > 0: v1 = v1 / np.linalg.norm(v1)
    if np.linalg.norm(v2) > 0: v2 = v2 / np.linalg.norm(v2)

    score = compute_cosine_similarity(v1, v2)
    print(f"-> Điểm tương đồng sinh trắc học: {score:.4f} (Ngưỡng an toàn: {THRESHOLD})")

    if score >= THRESHOLD:
        print(f"\n✅ KẾT LUẬN: GIAO DỊCH HỢP LỆ! Khuôn mặt khớp với chủ ID Ví [{wallet_id}].")
        return True
    else:
        print(f"\n❌ KẾT LUẬN: TỪ CHỐI GIAO DỊCH! Khuôn mặt không khớp với chủ ID Ví [{wallet_id}]. (Cosine: {score:.4f} < {THRESHOLD})")
        return False

if __name__ == "__main__":
    from run_public_server import get_local_ip, print_banner
    from app_server import app

    ip_addr = get_local_ip()
    print_banner(ip_addr, 5001)
    app.run(host='0.0.0.0', port=5001, debug=False)
