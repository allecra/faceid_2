# -*- coding: utf-8 -*-
"""
====================================================================
BỘ CHƯƠNG TRÌNH KHỞI CHẠY PUBLIC SERVER TEST TRÊN ĐIỆN THOẠI DI ĐỘNG
====================================================================
Chương trình này hỗ trợ:
1. Mạng nội bộ Wi-Fi (Cùng Wi-Fi): Gửi link http://<IP_WIFI>:5000
2. Mọi nơi trên thế giới qua Internet (4G/5G): Dùng LocalTunnel / Ngrok tạo Public HTTPS URL.
"""
import os
import sys
import socket

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from app_server import app

def get_local_ip():
    """Lấy địa chỉ IP mạng Wi-Fi/LAN của máy tính"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def print_banner(ip, port=5001):
    url_local = f"http://localhost:{port}"
    url_wifi = f"http://{ip}:{port}"
    
    print("="*75)
    print("📱 HỆ THỐNG MOBILE eKYC & FACEID TEST SERVER IS ONLINE!")
    print("="*75)
    print("\n🌐 BẠN CÓ THỂ CHỌN 1 TRONG 2 CÁCH DƯỚI ĐÂY ĐỂ GỬI LINK CHO NGƯỜI KHÁC:")
    print("-" * 75)
    print(f"📌 CÁCH 1: Người test bắt CÙNG MẠNG WI-FI với bạn (Mở Safari/Chrome trên ĐT):")
    print(f"   👉 LINK CHIA SẺ WI-FI:  {url_wifi}")
    print("-" * 75)
    print(f"📌 CÁCH 2: Người test ở KHÁC NƠI (Dùng 4G/5G từ xa trên toàn thế giới):")
    print(f"   Mở thêm 1 cửa sổ Terminal khác và chạy lệnh tạo Public HTTPS URL miễn phí:")
    print(f"   👉 Lệnh 1 (LocalTunnel):  npx -y localtunnel --port {port}")
    print(f"   👉 Lệnh 2 (Pinggy):       ssh -R 80:localhost:{port} a.pinggy.io")
    print("-" * 75)
    print("\n💡 HƯỚNG DẪN DÀNH CHO NGƯỜI DÙNG TEST:")
    print("   1. Mở link trên Safari (iOS) hoặc Chrome (Android).")
    print("   2. Cho phép quyền Camera khi ứng dụng yêu cầu.")
    print("   3. Đăng ký ID Ví ở Màn hình 1 -> Thử chuyển tiền > 10Tr ở Màn hình 2!")
    print("="*75 + "\n")

if __name__ == '__main__':
    ip_addr = get_local_ip()
    print_banner(ip_addr, 5001)
    app.run(host='0.0.0.0', port=5001, debug=False)
