import os
import sys
import urllib.request
from tqdm import tqdm

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình danh sách file cần tải từ repository chính thức của Silent-Face-Anti-Spoofing
BASE_URL = "https://github.com/minivision-ai/Silent-Face-Anti-Spoofing/raw/master/"

FILES_TO_DOWNLOAD = {
    "resources/detection_model/deploy.prototxt": BASE_URL + "resources/detection_model/deploy.prototxt",
    "resources/detection_model/Widerface-RetinaFace.caffemodel": BASE_URL + "resources/detection_model/Widerface-RetinaFace.caffemodel",
    "resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth": BASE_URL + "resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.pth",
    "resources/anti_spoof_models/4_0_0_80x80_MiniFASNetV1SE.pth": BASE_URL + "resources/anti_spoof_models/4_0_0_80x80_MiniFASNetV1SE.pth"
}

class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)

def download_file(url, output_path):
    # Đảm bảo thư mục cha tồn tại
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Downloading: {os.path.basename(output_path)} ...")
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc=os.path.basename(output_path)) as t:
        urllib.request.urlretrieve(url, filename=output_path, reporthook=t.update_to)
    print(f"Saved to: {output_path}\n")

if __name__ == "__main__":
    print("=" * 60)
    print("BO TAI TU DONG MO HINH MINI-FASNET LIVENESS MODEL")
    print("=" * 60)

    
    for path, url in FILES_TO_DOWNLOAD.items():
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            print(f"✨ File {path} đã tồn tại, bỏ qua không tải lại.")
        else:
            try:
                download_file(url, path)
            except Exception as e:
                print(f"❌ Lỗi khi tải file {path}: {e}")
                
    print("🎉 Hoàn tất quá trình tải mô hình! Bạn đã có thể chạy lại Server test.")
