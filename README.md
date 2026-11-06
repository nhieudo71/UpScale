# UpScale
Tăng độ phân giải ảnh miễn phí, xóa nền miễn phí

> Hiện tại app mới làm tính năng tăng độ phân giải (2x hoặc 4x). Xóa nền chưa có trong mã.

Ứng dụng Windows chạy hoàn toàn trên máy bạn: chọn ảnh PNG hoặc JPG, chọn 2x hoặc 4x, bấm Upscale. Ảnh kết quả `<tên>_x<hệ số>.png` được lưu cạnh ảnh gốc, ảnh gốc không bị sửa và file cùng tên không bị ghi đè. App không gọi mạng. Engine là [Real-ESRGAN ncnn Vulkan](https://github.com/xinntao/Real-ESRGAN), chạy bằng GPU qua Vulkan.

## Yêu cầu
- Windows với GPU hỗ trợ Vulkan (đã thử trên NVIDIA RTX 3050 Laptop 4 GB).
- Python 3.11 (dùng `tomllib`). Nếu máy có nhiều bản Python, dùng `py -3.11`.

## Cài đặt
```bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Engine không nằm trong repo (khoảng 51 MB). Tải `realesrgan-ncnn-vulkan-20220424-windows.zip` từ [Real-ESRGAN releases](https://github.com/xinntao/Real-ESRGAN/releases) và giải nén sao cho có:
```
engine\realesrgan\realesrgan-ncnn-vulkan.exe
engine\realesrgan\models\realesrgan-x4plus.param (và .bin)
engine\realesrgan\models\realesrgan-x4plus-anime.param (và .bin)
```
Thiếu engine thì app hiện màn hình hướng dẫn thay vì thoát.

## Chạy
```bat
run.bat
```
hoặc `.venv\Scripts\python.exe run.py`. Log nằm ở `logs\app.log`.

## Cấu hình
Chép `config.example.toml` thành `config.toml` cạnh `run.py` rồi sửa. Quan trọng nhất là `gpu_id`: máy có card onboard và card rời thì card rời thường là `1` (xem dòng `[1 NVIDIA ...]` trong `logs\app.log`). Xóa `config.toml` thì app dùng giá trị mặc định. Ý nghĩa từng khóa nằm trong file mẫu.

## Cần biết
- 2x chạy engine ở 4x rồi thu nhỏ về 2x, vì `-s 2` của engine cho ảnh sai nội dung (xem `docs/DECISIONS.md`, D-05). Do đó 2x tốn thời gian và VRAM như 4x.
- Ảnh có kết quả quá lớn (mặc định hơn 150 megapixel, tính ở 4x) bị chặn trước khi chạy.
- Thư mục chứa ảnh có ký tự Unicode (vd `_ĐẢNG`) chạy được. Riêng khi thư mục `%TEMP%` của Windows cũng có ký tự Unicode thì app báo lỗi và gợi ý chép ảnh sang thư mục không dấu (chưa thử trên máy như vậy).

## Phát triển
```bat
set PYTHONPATH=src
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -W error::ResourceWarning -m unittest discover -s tests -t .
.venv\Scripts\ruff.exe check src tests run.py
```
Test dùng engine giả (`tests/fake_engine.py`), không cần GPU.

Đóng gói: `.venv\Scripts\pyinstaller.exe --noconfirm --clean UpScale.spec` rồi `scripts\smoke_exe.ps1`. Thư mục `engine\` không được đóng gói, chép `engine\realesrgan` cạnh `UpScale.exe`.

## Tài liệu
`docs/PRD.md` (yêu cầu), `docs/SPRINT-1.md` (kế hoạch), `docs/ARCHITECTURE.md`, `docs/UX-UI-SPEC.md`, `docs/DECISIONS.md` (quyết định kỹ thuật và số đo), `tasklist.md` (tiến độ).

## Giấy phép
Engine `Real-ESRGAN-ncnn-vulkan` theo MIT, mã Real-ESRGAN theo BSD 3-Clause (đã đối chiếu file LICENSE trên GitHub). Giấy phép riêng của các file model chưa được xác nhận. Repo này chưa có file LICENSE của riêng nó.
