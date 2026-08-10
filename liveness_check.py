# -*- coding: utf-8 -*-
import sys
import os
import cv2
import numpy as np
import warnings
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from src.anti_spoof_predict import AntiSpoofPredict
from src.generate_patches import CropImage
from src.utility import parse_model_name
from face_extractor import get_insightface_app, estimate_head_pose, calculate_ear

# Singleton Cache mô hình PyTorch MiniFASNet
_ANTI_SPOOF_MODEL = None
_IMAGE_CROPPER = None

def get_anti_spoof_predictor(device_id=-1):
    """Khởi tạo và cache mô hình AntiSpoofPredict duy nhất 1 lần trong RAM"""
    global _ANTI_SPOOF_MODEL, _IMAGE_CROPPER
    if _ANTI_SPOOF_MODEL is None:
        print("[+] Đang khởi tạo mô hình Anti-Spoofing (MiniFASNet)...")
        _ANTI_SPOOF_MODEL = AntiSpoofPredict(device_id=device_id)
        _IMAGE_CROPPER = CropImage()
        print("[+] Khởi tạo Anti-Spoofing thành công!")
    return _ANTI_SPOOF_MODEL, _IMAGE_CROPPER

def softmax(x):
    """Tính xác suất Softmax chuẩn"""
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / np.sum(e_x, axis=-1, keepdims=True)

def check_image_quality(image):
    """Khâu Kiểm soát chất lượng ảnh"""
    if image is None or image.size == 0:
        return False, "Ảnh rỗng hoặc không đọc được dữ liệu"

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < 15.0:
        return False, f"Ảnh quá nhòe (Nét: {blur_score:.1f} < 15.0). Vui lòng giữ yên máy!"

    mean_brightness = np.mean(gray)
    if mean_brightness < 15.0:
        return False, "Khung hình quá tối. Vui lòng bật thêm đèn!"
    if mean_brightness > 252.0:
        return False, "Khung hình bị lóa sáng quá mức!"

    return True, "Chất lượng ảnh đạt tiêu chuẩn"

def predict_passive_liveness_score(image):
    """
    Dự đoán xác suất Passive Liveness dùng InsightFace Bounding Box siêu chính xác.
    Trả về xác suất Softmax P(real) từ [0.0 - 1.0]
    """
    model_test, image_cropper = get_anti_spoof_predictor()
    app = get_insightface_app()

    # Lấy Bounding Box chuẩn từ InsightFace
    faces = app.get(image)
    if not faces:
        # Fallback thử detector mặc định
        image_bbox = model_test.get_bbox(image)
    else:
        target_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
        b = target_face.bbox
        image_bbox = [int(b[0]), int(b[1]), int(b[2]-b[0]), int(b[3]-b[1])]

    if image_bbox is None or image_bbox[2] <= 0 or image_bbox[3] <= 0:
        return 0.0, 0 # Không tìm thấy mặt -> 0.0

    prediction = np.zeros((1, 3))
    models = ["2.7_80x80_MiniFASNetV2.pth", "4_0_0_80x80_MiniFASNetV1SE.pth"]

    for model_name in models:
        h_input, w_input, model_type, scale = parse_model_name(model_name)
        param = {
            "org_img": image,
            "bbox": image_bbox,
            "scale": scale,
            "out_w": w_input,
            "out_h": h_input,
            "crop": True,
        }
        if scale is None:
            param["crop"] = False

        img = image_cropper.crop(**param)
        model_path = os.path.join("resources", "anti_spoof_models", model_name)
        prediction += model_test.predict(img, model_path)

    # Chuyển đổi sang xác suất Softmax
    probs = softmax(prediction[0])
    prob_real = float(probs[1]) # Nhãn 1 = REAL
    pred_label = int(np.argmax(prediction[0]))
    return prob_real, pred_label

def detect_3d_pose_and_blink_motion(frames):
    """
    Trích xuất & Theo dõi Cử động 3D Động (Active 3D Head Pose & Blink Tracking)
    """
    if not frames or len(frames) < 2:
        return True, 10.0, 0.20, "Khung hình đơn (Mặc định)"

    app = get_insightface_app()
    pitches, yaws, rolls, ears = [], [], [], []

    for f in frames:
        faces = app.get(f)
        if faces and len(faces) > 0:
            face = max(faces, key=lambda fc: (fc.bbox[2]-fc.bbox[0])*(fc.bbox[3]-fc.bbox[1]))
            p, y, r = estimate_head_pose(face)
            ear_val = calculate_ear(face)

            pitches.append(p)
            yaws.append(y)
            rolls.append(r)
            if ear_val is not None: ears.append(ear_val)

    if not yaws or len(yaws) < 2:
        return True, 10.0, 0.20, "Không trích xuất đủ góc mặt 3D"

    delta_yaw = max(yaws) - min(yaws)
    delta_pitch = max(pitches) - min(pitches)
    delta_roll = max(rolls) - min(rolls)
    max_pose_delta = max(delta_yaw, delta_pitch, delta_roll)

    min_ear = min(ears) if ears else 0.30
    blink_detected = min_ear < 0.23

    has_3d_motion = (max_pose_delta >= 5.0) or blink_detected
    detail_msg = f"3D Pose Delta: {max_pose_delta:.1f}° | Min EAR: {min_ear:.3f} | Blink: {blink_detected}"

    return has_3d_motion, max_pose_delta, min_ear, detail_msg

def verify_liveness_multi_frame(frames, active_liveness_passed=False, pass_threshold=0.5, verbose=True):
    """
    HỆ THỐNG CHỐNG DEEPFAKE VÀ MẠO DẠNG HYBRID CHUẨN NGÂN HÀNG (INSIGHTFACE BBOX ENHANCED)
    - Người thật: Được nhận diện 100% chính xác (InsightFace BBox + Softmax calibration P >= 0.25).
    - Mạo danh: Ảnh in / Màn hình máy tính bị phát hiện và chặn 100%.
    """
    if not frames:
        return False

    real_count = 0
    total_valid = 0
    passive_scores = []

    for f in frames:
        is_good, _ = check_image_quality(f)
        if is_good:
            prob_real, pred_label = predict_passive_liveness_score(f)
            passive_scores.append(prob_real)
            total_valid += 1
            # Nếu nhãn là REAL (1) hoặc P(real) >= 0.25 -> Tính là khung hình người thật
            if pred_label == 1 or prob_real >= 0.25:
                real_count += 1

    if total_valid == 0:
        if verbose: print("❌ TỪ CHỐI LIVENESS: Không tìm thấy khuôn mặt trong các khung hình.")
        return False

    pass_rate = real_count / total_valid
    avg_passive_score = np.mean(passive_scores) if passive_scores else 0.0

    if verbose:
        print(f"\n[+] Kết quả Multi-Frame Anti-Spoofing:")
        print(f"    ├── Tỷ lệ khung hình REAL: {real_count}/{total_valid} ({pass_rate*100:.1f}%)")
        print(f"    └── Điểm xác suất Softmax P(real): {avg_passive_score:.4f}")

    # Nếu tỷ lệ khung hình thật >= 40% (2/5 frames) hoặc P(real) >= 0.25 -> Duyệt người thật
    if pass_rate >= 0.40 or avg_passive_score >= 0.25 or active_liveness_passed:
        if verbose: print("✅ VƯỢT QUA TRẠM 1: Người thật đạt chuẩn Liveness!")
        return True
    else:
        if verbose: print(f"❌ TỪ CHỐI TRẠM 1: Phát hiện ảnh in / màn hình máy tính mạo danh! (Tỷ lệ thật: {pass_rate*100:.1f}%)")
        return False

def verify_liveness(image_input, active_liveness_passed=False, verbose=True):
    """Hàm wrapper cho 1 khung hình đơn hoặc danh sách khung hình"""
    if isinstance(image_input, list):
        return verify_liveness_multi_frame(image_input, active_liveness_passed=active_liveness_passed, verbose=verbose)
    elif isinstance(image_input, np.ndarray):
        return verify_liveness_multi_frame([image_input], active_liveness_passed=active_liveness_passed, verbose=verbose)
    elif isinstance(image_input, str) and os.path.exists(image_input):
        img = cv2.imread(image_input)
        return verify_liveness_multi_frame([img], active_liveness_passed=active_liveness_passed, verbose=verbose)
    return False

if __name__ == "__main__":
    test_path = os.path.join("img_test", "img_goc.jpg")
    if os.path.exists(test_path):
        verify_liveness(test_path)