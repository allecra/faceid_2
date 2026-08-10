# -*- coding: utf-8 -*-
"""
MODULE KIỂM TRA QUY CHUẨN eKYC TỰ ĐỘNG (COMPLIANCE PRE-CHECK)
Kiểm tra 5 tiêu chuẩn nghiêm ngặt trước khi cho phép chụp eKYC:
1. Ánh sáng môi trường đủ sáng (Brightness > 60)
2. Không bị nhòe mờ (Blur score > 30)
3. Không đeo khẩu trang / Che mặt (No Face Mask)
4. Không đeo kính mắt (No Glasses)
5. Không đội mũ / Phải để lộ rõ trán (No Hat & Forehead Exposed)
"""
import sys
import os
import cv2
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def check_lighting_and_blur(image):
    """1. Kiểm tra Ánh sáng & Độ nhòe"""
    if image is None or image.size == 0:
        return False, "Khung hình rỗng hoặc không có dữ liệu camera."

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Kiểm tra Độ sáng (Brightness)
    mean_brightness = np.mean(gray)
    if mean_brightness < 55.0:
        return False, f"⚠️ Môi trường quá tối (Độ sáng: {mean_brightness:.1f}/255). Vui lòng di chuyển đến nơi sáng hơn!"
    if mean_brightness > 245.0:
        return False, f"⚠️ Ánh sáng bị lóa quá mức (Độ sáng: {mean_brightness:.1f}/255). Vui lòng tránh ánh sáng chiếu thẳng vào camera!"

    # Kiểm tra Độ nhòe (Blurness)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_score < 28.0:
        return False, f"⚠️ Khung hình bị nhòe mờ (Độ nét: {blur_score:.1f}). Vui lòng giữ yên điện thoại!"

    return True, "Ánh sáng và độ nét đạt chuẩn"

def check_mask_occlusion(image, kps, bbox):
    """2. Phát hiện Khẩu trang / Che nửa dưới khuôn mặt"""
    if kps is None or len(kps) < 5:
        return True, "Không đủ keypoints để kiểm tra khẩu trang"

    # kps: [right_eye, left_eye, nose, right_mouth, left_mouth]
    nose = kps[2]
    mouth_r = kps[3]
    mouth_l = kps[4]

    # Cắt vùng mũi - cằm (Lower Face)
    x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
    h, w = image.shape[:2]
    
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    lower_y1 = int(nose[1])
    lower_y2 = y2
    lower_x1 = max(0, int(min(mouth_r[0], mouth_l[0])) - 15)
    lower_x2 = min(w, int(max(mouth_r[0], mouth_l[0])) + 15)

    if lower_y2 > lower_y1 and lower_x2 > lower_x1:
        lower_face = image[lower_y1:lower_y2, lower_x1:lower_x2]
        if lower_face.size > 0:
            hsv = cv2.cvtColor(lower_face, cv2.COLOR_BGR2HSV)
            # Kiểm tra tỷ lệ màu da trong vùng miệng/cằm
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            mask_skin = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_ratio = np.sum(mask_skin > 0) / (lower_face.shape[0] * lower_face.shape[1])

            # Nếu tỷ lệ màu da ở vùng miệng < 25% -> Đang đeo khẩu trang
            if skin_ratio < 0.22:
                return False, "⚠️ Phát hiện đeo khẩu trang hoặc che miệng! Vui lòng tháo khẩu trang để lộ rõ cằm và miệng."

    return True, "Không đeo khẩu trang"

def check_glasses(image, kps):
    """3. Phát hiện Đeo kính mắt (Glasses Detection)"""
    if kps is None or len(kps) < 5:
        return True, "Không đủ keypoints để kiểm tra kính mắt"

    r_eye = kps[0]
    l_eye = kps[1]

    # Cắt vùng xung quanh 2 mắt và gọng kính giữa 2 mắt
    eye_x1 = max(0, int(min(r_eye[0], l_eye[0])) - 20)
    eye_x2 = min(image.shape[1], int(max(r_eye[0], l_eye[0])) + 20)
    eye_y1 = max(0, int(min(r_eye[1], l_eye[1])) - 15)
    eye_y2 = min(image.shape[0], int(max(r_eye[1], l_eye[1])) + 15)

    if eye_y2 > eye_y1 and eye_x2 > eye_x1:
        eye_region = image[eye_y1:eye_y2, eye_x1:eye_x2]
        gray_eye = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
        
        # Mật độ Cạnh (Edge Density) từ gọng kính
        edges = cv2.Canny(gray_eye, 80, 180)
        edge_density = np.sum(edges > 0) / (eye_region.shape[0] * eye_region.shape[1])

        # Phản chiếu / Phản xạ ánh sáng trên mắt kính (Glare / Contrast)
        std_dev = np.std(gray_eye)

        # Nếu mật độ cạnh và độ tương phản xung quanh mắt quá cao -> Đang đeo kính
        if edge_density > 0.28 and std_dev > 45.0:
            return False, "⚠️ Phát hiện đeo kính mắt! Vui lòng tháo kính trước khi chụp eKYC."

    return True, "Không đeo kính mắt"

def check_hat_and_forehead(image, kps, bbox):
    """4 & 5. Phát hiện Đội mũ & Yêu cầu để lộ rõ trán (Hat & Forehead Exposure)"""
    if bbox is None:
        return True, "Không có bbox"

    x1, y1, x2, y2 = [int(v) for v in bbox[:4]]
    h, w = image.shape[:2]
    
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)

    # Vùng Trán (Top 25% của Bounding Box)
    forehead_height = int((y2 - y1) * 0.30)
    forehead_y1 = max(0, y1 - int(forehead_height * 0.4))
    forehead_y2 = min(h, y1 + forehead_height)
    forehead_x1 = max(0, x1 + int((x2 - x1) * 0.15))
    forehead_x2 = min(w, x2 - int((x2 - x1) * 0.15))

    if forehead_y2 > forehead_y1 and forehead_x2 > forehead_x1:
        forehead_crop = image[forehead_y1:forehead_y2, forehead_x1:forehead_x2]
        if forehead_crop.size > 0:
            hsv = cv2.cvtColor(forehead_crop, cv2.COLOR_BGR2HSV)
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([20, 255, 255], dtype=np.uint8)
            mask_skin = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_ratio = np.sum(mask_skin > 0) / (forehead_crop.shape[0] * forehead_crop.shape[1])

            # Nếu vùng trán/đỉnh đầu bị màu tối của mũ hoặc tóc che hết (skin_ratio < 20%) -> Đội mũ / che trán
            if skin_ratio < 0.18:
                return False, "⚠️ Phát hiện đội mũ hoặc trán bị che khuất! Vui lòng tháo mũ và để lộ rõ trán."

    return True, "Để lộ rõ trán và không đội mũ"

def verify_full_ekyc_compliance(image, face_object=None):
    """
    HÀM TỔNG HỢP KIỂM TRA ĐẦY ĐỦ 5 QUY CHUẨN eKYC:
    Trả về: (is_passed: bool, message: str)
    """
    # 1. Ánh sáng & Độ nhòe
    ok_light, msg_light = check_lighting_and_blur(image)
    if not ok_light:
        return False, msg_light

    if face_object is not None:
        bbox = face_object.get('bbox')
        kps = face_object.get('kps')

        # 2. Phát hiện Khẩu trang
        ok_mask, msg_mask = check_mask_occlusion(image, kps, bbox)
        if not ok_mask:
            return False, msg_mask

        # 3. Phát hiện Kính mắt
        ok_glass, msg_glass = check_glasses(image, kps)
        if not ok_glass:
            return False, msg_glass

        # 4 & 5. Phát hiện Đội mũ & Để lộ trán
        ok_hat, msg_hat = check_hat_and_forehead(image, kps, bbox)
        if not ok_hat:
            return False, msg_hat

    return True, "✅ Tất cả quy chuẩn eKYC đạt chuẩn: Đủ sáng, Không kính, Không khẩu trang, Không mũ, Rõ trán!"
