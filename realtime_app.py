# -*- coding: utf-8 -*-
import sys
import os
import cv2
import time
import random
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from main import verify_transaction
from face_extractor import get_insightface_app, calculate_ear, estimate_head_pose

CHALLENGES = [
    {"id": "BLINK", "text": "CHOP MAT (Eye Blink)", "icon": "👁️"},
    {"id": "LEFT", "text": "QUAY SANG TRAI (Turn Left)", "icon": "👈"},
    {"id": "RIGHT", "text": "QUAY SANG PHAI (Turn Right)", "icon": "👉"},
    {"id": "DOWN", "text": "CUI MAT XUONG (Tilt Down)", "icon": "⬇️"},
    {"id": "UP", "text": "NGUA MAT LEN (Tilt Up)", "icon": "⬆️"}
]

def get_camera():
    """Tự động kết nối camera (thử index 0 trước, sau đó 1)"""
    for cam_idx in [0, 1]:
        cap = cv2.VideoCapture(cam_idx)
        if cap.isOpened():
            print(f"[+] Kết nối Camera thành công (Index: {cam_idx})")
            return cap
    return None

def run_realtime_face_id(user_id):
    cap = get_camera()
    if cap is None:
        print("[!] Lỗi: Không thể mở Camera.")
        return

    app = get_insightface_app()

    # Chọn ngẫu nhiên thử thách Active Liveness ban đầu
    current_challenge = random.choice(CHALLENGES)
    blink_counter = 0

    print("="*60)
    print(f"HỆ THỐNG XÁC THỰC FACE ID SECURE - KHÁCH HÀNG: [{user_id}]")
    print(f"-> Thử thách Active Liveness: [{current_challenge['text']}]")
    print("-> Nhấn 'V' để duyệt thủ công | Nhấn 'R' để đổi thử thách | Nhấn 'Q' để thoát.")
    print("="*60)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        start_point = (w//4, h//6)
        end_point = (w*3//4, h*5//6)
        
        faces = app.get(frame)
        current_ear = None
        pitch, yaw, roll = 0.0, 0.0, 0.0
        active_passed = False

        if len(faces) > 0:
            target_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
            current_ear = calculate_ear(target_face)
            pitch, yaw, roll = estimate_head_pose(target_face)

            # Kiểm tra xem người dùng có hoàn thành thử thách Active Liveness hiện tại không
            cid = current_challenge['id']
            if cid == "BLINK":
                if current_ear is not None and current_ear < 0.20:
                    blink_counter += 1
                elif current_ear is not None and current_ear > 0.24 and blink_counter > 0:
                    active_passed = True
                    blink_counter = 0
            elif cid == "LEFT" and yaw < -12.0:
                active_passed = True
            elif cid == "RIGHT" and yaw > 12.0:
                active_passed = True
            elif cid == "DOWN" and pitch > 10.0:
                active_passed = True
            elif cid == "UP" and pitch < -10.0:
                active_passed = True

        # --- UI OVERLAY ---
        box_color = (0, 255, 255) # Mặc định Vàng Cyan
        if active_passed:
            box_color = (0, 255, 0) # Đạt màu Xanh lá

        cv2.rectangle(frame, start_point, end_point, box_color, 2)
        cv2.putText(frame, "HE THONG FACE ID eKYC BANKING", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Hiển thị câu lệnh thử thách
        prompt_str = f"THU THACH: {current_challenge['icon']} {current_challenge['text']}"
        cv2.putText(frame, prompt_str, (20, 65), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)

        # Hiển thị thông số Pose real-time
        pose_str = f"Pitch: {pitch:.1f} | Yaw: {yaw:.1f} | EAR: {(current_ear if current_ear else 0):.2f}"
        cv2.putText(frame, pose_str, (20, 95), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        cv2.imshow("He Thong Face ID - Secure Transaction", frame)

        key = cv2.waitKey(1) & 0xFF
        trigger_verify = False

        if key == ord('q'):
            break
        elif key == ord('r'):
            current_challenge = random.choice(CHALLENGES)
            print(f"\n[+] Đổi thử thách mới: [{current_challenge['text']}]")
        elif key == ord('v') or active_passed:
            trigger_verify = True
            reason_str = "Phím V (Thủ công)" if key == ord('v') else f"ACTIVE POSE OK [{current_challenge['id']}]"
            print(f"\n[+] KÍCH HOẠT XÁC THỰC BẰNG: {reason_str}")

        if trigger_verify:
            # 1. Hiển thị trạng thái đang quét
            cv2.putText(frame, "ACTIVE LIVENESS PASSED! DANG VERIFY...", (w//4 - 30, h//2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("He Thong Face ID - Secure Transaction", frame)
            cv2.waitKey(150)

            # 2. Thu thập 12 frames RAM cho Multi-Frame Voting
            frames_buffer = []
            for i in range(12):
                r, f = cap.read()
                if r:
                    f = cv2.flip(f, 1)
                    frames_buffer.append(f)
                time.sleep(0.02)

            if not frames_buffer:
                frames_buffer = [frame]

            # 3. Tiến hành Xác thực 2 Trạm với Active Liveness Passed Flag
            is_valid = verify_transaction(user_id, frames_buffer, active_liveness_passed=True)

            # 4. Hiển thị kết quả trên màn hình
            last_frame = frames_buffer[-1].copy()
            if is_valid:
                cv2.rectangle(last_frame, start_point, end_point, (0, 255, 0), 4)
                cv2.putText(last_frame, "GIAO DICH HOP LE!", (w//4 - 10, h - 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            else:
                cv2.rectangle(last_frame, start_point, end_point, (0, 0, 255), 4)
                cv2.putText(last_frame, "TU CHOI GIAO DICH!", (w//4 - 10, h - 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

            cv2.imshow("He Thong Face ID - Secure Transaction", last_frame)
            cv2.waitKey(3000)

            # Chọn thử thách mới cho lần tiếp theo
            current_challenge = random.choice(CHALLENGES)
            print(f"[+] Thử thách mới tiếp theo: [{current_challenge['text']}]")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    ID_KHACH_HANG = "0987654321" 
    run_realtime_face_id(ID_KHACH_HANG)