# 🛡️ Secure Mobile FaceID & eKYC Banking System

Hệ thống sinh trắc học eKYC 5 góc mặt & Xác thực FaceID 2 trạm duyệt giao dịch tài chính (> 10 Triệu VNĐ) chuẩn Quyết định 2345/QĐ-NHNN.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

1. **eKYC Đăng Ký 5 Góc Mặt (Sequential 5-Pose Tour)**:
   - Hướng dẫn người dùng chụp 5 góc mặt (Quay trái 30°-45°, Quay phải 30°-45°, Cúi 20°-30°, Ngửa 20°-30°, Nhìn thẳng).
   - Tự động mã hóa **Master Vector 512D Ensemble** lưu vào Cloud Vector DB.
   - Tải mảng 5 ảnh mặt thật lên **Cloudinary Media Library cá nhân**.

2. **Bộ Lọc 5 Quy Chuẩn eKYC Bảo Mật (Compliance Pre-Check)**:
   - 💡 Môi trường đủ sáng ($15 \le \text{Brightness} \le 252$).
   - 👓 Bắt buộc tháo kính mắt.
   - 😷 Bắt buộc tháo khẩu trang / che cằm.
   - 🧢 Bắt buộc tháo mũ.
   - 👤 Bắt buộc để lộ rõ trán.

3. **Anti-Spoofing Hybrid Fusion (Chống Deepfake Chuẩn Ngân Hàng)**:
   - **Passive Softmax Calibration**: PyTorch MiniFASNet V2 & V1SE ($P(\text{real}) \ge 0.35$).
   - **InsightFace Bounding Box Integration**: Cắt patch khuôn mặt siêu chính xác từ camera di động.
   - **Active 3D Motion Tracking**: Theo dõi độ biến thiên góc quay 3D $\Delta \text{Pose}_{3D} \ge 7^\circ$ hoặc chớp mắt $\text{EAR} < 0.22$.

4. **FaceID 2 Trạm Duyệt Chuyển Tiền (> 10M VNĐ)**:
   - **Trạm 1**: Anti-Spoofing & 3D Motion Check.
   - **Trạm 2**: So khớp Cosine Similarity 512D với Cloud DB ($\text{Threshold} = 0.40$).

---

## 🚀 Khởi Chạy Server (Quick Start)

### 1. Cài đặt thư viện Python:
```bash
pip install -r requirements.txt
pip install cloudinary
```

### 2. Cấu hình Cloudinary cá nhân:
Điền `cloud_name`, `api_key`, `api_secret` của bạn vào file `cloudinary_config.json`.

### 3. Chạy Server Public:
```bash
python run_public_server.py
```
- **Máy tính / Cùng mạng Wi-Fi**: Mở `http://localhost:5000` hoặc `http://192.168.x.x:5000`.
- **Người dùng từ xa (4G/5G)**: Chạy thêm `npx -y localtunnel --port 5000`.

---

## 🌐 REST API Endpoints Cho Developer

### 🔹 API 1: Đăng ký eKYC Đa Góc Mặt (`POST /api/register_ekyc`)
```json
{
  "user_id": "0x71C89A3B21",
  "images": [
    "data:image/jpeg;base64,...",
    "data:image/jpeg;base64,...",
    "data:image/jpeg;base64,...",
    "data:image/jpeg;base64,...",
    "data:image/jpeg;base64,..."
  ]
}
```

### 🔹 API 2: Xác thực FaceID Duyệt Chuyển Tiền (`POST /api/verify_faceid`)
```json
{
  "user_id": "0x71C89A3B21",
  "images": [
    "data:image/jpeg;base64,...",
    "data:image/jpeg;base64,..."
  ],
  "active_liveness_passed": false
}
```
