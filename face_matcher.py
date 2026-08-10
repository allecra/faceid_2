import os
import cv2
import numpy as np
from numpy.linalg import norm
from face_extractor import extract_embedding, get_insightface_app

def compute_cosine_similarity(vec1, vec2):
    """Tính tích vô hướng chia cho tích độ dài của 2 vector (Cosine Similarity)"""
    if vec1 is None or vec2 is None:
        return 0.0
    norm_1 = norm(vec1)
    norm_2 = norm(vec2)
    if norm_1 == 0 or norm_2 == 0:
        return 0.0
    similarity = np.dot(vec1, vec2) / (norm_1 * norm_2)
    return float(similarity)

def get_face_embedding(image_input):
    """
    Trích xuất vector 512D từ đường dẫn file hoặc khung hình numpy array trong RAM.
    """
    app = get_insightface_app()
    return extract_embedding(image_input, app=app)

if __name__ == "__main__":
    IMAGE_DB = os.path.join("img_test", "img_goc.jpg")
    IMAGE_CAMERA = os.path.join("img_test", "img-giao-dich.jpg")
    THRESHOLD = 0.45 

    if os.path.exists(IMAGE_DB) and os.path.exists(IMAGE_CAMERA):
        print("\n[1] Đang truy xuất dữ liệu khuôn mặt từ Database (Ảnh gốc)...")
        vector_db = get_face_embedding(IMAGE_DB)

        print("[2] Đang xử lý khuôn mặt từ Camera (Ảnh giao dịch)...")
        vector_camera = get_face_embedding(IMAGE_CAMERA)

        if vector_db is not None and vector_camera is not None:
            print("\n[3] Bắt đầu đối chiếu dữ liệu sinh trắc học...")
            score = compute_cosine_similarity(vector_db, vector_camera)
            print(f" -> Điểm tương đồng (Cosine Similarity): {score:.4f}")
            
            if score >= THRESHOLD:
                print("\n✅ KẾT QUẢ: XÁC THỰC THÀNH CÔNG!")
            else:
                print("\n❌ KẾT QUẢ: TỪ CHỐI GIAO DỊCH!")