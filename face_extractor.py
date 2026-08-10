import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis

_INSIGHTFACE_APP = None

def get_insightface_app(name='buffalo_l', ctx_id=-1, det_size=(640, 640)):
    """Singleton: Khởi tạo và lưu mô hình InsightFace duy nhất 1 lần trong bộ nhớ RAM"""
    global _INSIGHTFACE_APP
    if _INSIGHTFACE_APP is None:
        print("[+] Đang khởi tạo mô hình InsightFace (buffalo_l)...")
        _INSIGHTFACE_APP = FaceAnalysis(name=name)
        _INSIGHTFACE_APP.prepare(ctx_id=ctx_id, det_size=det_size)
        print("[+] Khởi tạo InsightFace thành công!")
    return _INSIGHTFACE_APP

def calculate_ear(face):
    """
    Tính chỉ số Eye Aspect Ratio (EAR) để phát hiện chớp mắt.
    Trả về giá trị EAR trung bình 2 mắt (< 0.20 khi nhắm mắt, > 0.25 khi mở mắt).
    """
    if hasattr(face, 'landmark_3d_68') and face.landmark_3d_68 is not None:
        landmarks = face.landmark_3d_68[:, :2]
        def ear_68(pts):
            p1, p2, p3, p4, p5, p6 = pts[0], pts[1], pts[2], pts[3], pts[4], pts[5]
            v1 = np.linalg.norm(p2 - p6)
            v2 = np.linalg.norm(p3 - p5)
            h = np.linalg.norm(p1 - p4)
            return (v1 + v2) / (2.0 * h + 1e-6)
        
        left_ear = ear_68(landmarks[36:42])
        right_ear = ear_68(landmarks[42:48])
        return (left_ear + right_ear) / 2.0
    
    elif hasattr(face, 'landmark_2d_106') and face.landmark_2d_106 is not None:
        lm = face.landmark_2d_106
        def dist(p1, p2):
            return np.linalg.norm(lm[p1] - lm[p2])
        left_ear = dist(37, 41) / (dist(33, 39) + 1e-6)
        right_ear = dist(89, 95) / (dist(87, 93) + 1e-6)
        return (left_ear + right_ear) / 2.0

    return None

def estimate_head_pose(face):
    """
    Ước tính góc quay khuôn mặt (Pitch, Yaw, Roll) theo độ (Degrees).
    - Pitch: > 10 (Cúi mặt), < -10 (Ngửa mặt)
    - Yaw: < -12 (Quay trái), > +12 (Quay phải)
    """
    if hasattr(face, 'pose') and face.pose is not None and len(face.pose) == 3:
        # pitch, yaw, roll từ InsightFace 3D pose
        return float(face.pose[0]), float(face.pose[1]), float(face.pose[2])
    
    # Fallback ước tính từ 5 keypoints (kps)
    if hasattr(face, 'kps') and face.kps is not None and len(face.kps) == 5:
        kps = face.kps
        left_eye, right_eye, nose, left_mouth, right_mouth = kps[0], kps[1], kps[2], kps[3], kps[4]
        
        # Yaw (Quay trái/phải)
        eye_center_x = (left_eye[0] + right_eye[0]) / 2.0
        eye_dist_x = abs(right_eye[0] - left_eye[0]) + 1e-6
        dx = nose[0] - eye_center_x
        yaw = (dx / eye_dist_x) * 50.0

        # Pitch (Cúi/Ngửa mặt)
        eye_center_y = (left_eye[1] + right_eye[1]) / 2.0
        mouth_center_y = (left_mouth[1] + right_mouth[1]) / 2.0
        upper_h = nose[1] - eye_center_y
        lower_h = mouth_center_y - nose[1] + 1e-6
        pitch_ratio = upper_h / lower_h
        pitch = (pitch_ratio - 0.75) * 45.0

        # Roll (Nghiêng)
        dy = right_eye[1] - left_eye[1]
        roll = np.degrees(np.arctan2(dy, eye_dist_x))

        return float(pitch), float(yaw), float(roll)

    return 0.0, 0.0, 0.0

def extract_embedding(image_input, app=None):
    """Trích xuất vector 512D từ filepath hoặc numpy array RAM"""
    if app is None:
        app = get_insightface_app()

    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            return None
        img = cv2.imread(image_input)
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        return None

    if img is None or img.size == 0:
        return None

    faces = app.get(img)
    if len(faces) == 0:
        return None

    target_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
    return target_face.embedding

if __name__ == "__main__":
    test_path = os.path.join("img_test", "img_goc.jpg")
    if os.path.exists(test_path):
        app = get_insightface_app()
        faces = app.get(cv2.imread(test_path))
        if len(faces) > 0:
            pitch, yaw, roll = estimate_head_pose(faces[0])
            print(f"Head Pose -> Pitch: {pitch:.1f}°, Yaw: {yaw:.1f}°, Roll: {roll:.1f}°")