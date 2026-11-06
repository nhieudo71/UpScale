# Quyết định kỹ thuật

**Cập nhật**: 11/06/2026

## D-01: Engine upscale = Real-ESRGAN ncnn Vulkan v0.2.0 (Spike ngày 1, US-01)

**Kết luận spike**: engine chạy được trên GPU NVIDIA của máy, offline, trả đúng kích thước. Cổng quyết định cuối ngày 1 được thông qua, không cần phương án dự phòng.

### Môi trường đã kiểm tra trên máy
| Hạng mục | Kết quả |
|---|---|
| GPU (`nvidia-smi`) | NVIDIA GeForce RTX 3050 Laptop, 4096 MiB, driver 572.42 |
| VRAM đang bị dùng sẵn | 691 MiB trước khi chạy, nên còn khoảng 3.4 GB |
| Vulkan thấy 2 thiết bị | `[0] Intel UHD Graphics`, `[1] RTX 3050 Laptop GPU` |
| Python | 3.11.9, pip 26.3, Tkinter 8.6, git 2.55 |
| Python mặc định của `py` | 3.14 (khác với `python` là 3.11.9) |

### Nguồn engine
- Tải từ Real-ESRGAN release v0.2.5.0, file `realesrgan-ncnn-vulkan-20220424-windows.zip` (45.474.481 byte, khớp kích thước GitHub báo).
- SHA256: `ABC02804E17982A3BE33675E4D471E91EA374E65B70167ABC09E31ACB412802D`. Đây là hash tôi tính sau khi tải. GitHub không công bố hash để đối chiếu.
- Bản `realesrgan-ncnn-vulkan-v0.2.0-windows.zip` trong repo ncnn-vulkan chỉ có file thực thi, không có model, nên không dùng.
- Vị trí trong dự án: `engine/realesrgan/` (có `realesrgan-ncnn-vulkan.exe` và thư mục `models/`).
- Giấy phép: file LICENSE đi kèm là MIT. Giấy phép của riêng các file model chưa được kiểm tra.

### Model có sẵn
`realesrgan-x4plus` (ảnh thật), `realesrgan-x4plus-anime`, `realesr-animevideov3-x2`, `-x3`, `-x4`.

### Kết quả chạy thử (ảnh 220x220, một ảnh duy nhất)
| Lệnh | Kết quả | Thời gian |
|---|---|---|
| `-n realesrgan-x4plus -s 4` (tự chọn GPU) | 880x880, exit 0 | 6,13 s |
| `-n realesr-animevideov3 -s 2` (tự chọn GPU) | 440x440, exit 0 | 2,95 s |
| `-n realesrgan-x4plus -s 4 -g 0` (Intel) | exit 0 | 14,15 s |
| `-n realesrgan-x4plus -s 4 -g 1` (RTX 3050) | exit 0 | 5,07 s |

Kiểm tra ảnh kết quả: kích thước đúng, độ sáng trung bình khoảng 127,5 nên không phải ảnh đen (README engine có ghi nhận lỗi ảnh đen trên một số máy). Đây chỉ là kiểm tra thô bằng số liệu, tôi chưa xem ảnh bằng mắt.

### Điều rút ra cho thiết kế
1. **Chọn GPU rõ ràng bằng `-g`.** Máy có 2 GPU và Intel chậm hơn gần 3 lần. Tôi không biết chế độ tự chọn dùng GPU nào, vì lần chạy tự chọn (6,13 s) gồm cả thời gian khởi động lần đầu. Ứng dụng nên cho cấu hình `gpu_id` và mặc định là GPU NVIDIA. Không nên cố định chỉ số 1, vì chỉ số có thể đổi khi driver hoặc máy thay đổi.
2. **Tiến trình in ra stderr.** Engine ghi cả log lẫn phần trăm tiến độ vào stderr. Trong PowerShell, việc này hiện thành `NativeCommandError` dù exit code là 0. Ứng dụng phải dựa vào exit code, không dựa vào việc stderr có nội dung.
3. **Phần trăm theo định dạng ngôn ngữ máy.** Tiến độ in dạng `25,00%` (dấu phẩy). Bộ phân tích tiến độ phải chấp nhận cả dấu phẩy và dấu chấm.
4. **Chế độ 2x cho ảnh thật chạy được.** Model ảnh thật `realesrgan-x4plus` chỉ có bản x4, nhưng `-n realesrgan-x4plus -s 2 -g 1` vẫn chạy xong (exit 0) và trả 440x440 từ ảnh 220x220. Tôi mới kiểm tra kích thước, chưa xem chất lượng bằng mắt, nên chưa biết kết quả 2x của model này có tốt hơn model anime hay không. Phương án dự phòng nếu chất lượng kém là chạy x4 rồi thu nhỏ về 2x bằng Pillow.

### Thử ảnh lớn (US-04, một lần chạy duy nhất)
| Mục | Kết quả |
|---|---|
| Ảnh vào | 1000x1000 (1 megapixel), ảnh tổng hợp gồm dải màu và nhiễu ngẫu nhiên, không phải ảnh chụp |
| Lệnh | `-n realesrgan-x4plus -s 4 -g 1`, tile tự động (mặc định) |
| Đầu ra | 4000x4000, file được tạo ra |
| Thời gian | 16,5 s, thấp hơn ngưỡng tạm 60 s của PRD |
| VRAM đỉnh toàn GPU | 1957 MiB, lấy mẫu `nvidia-smi` mỗi 0,5 s. Đã trừ 691 MiB dùng sẵn thì engine dùng khoảng 1,3 GB |

Hạn chế của phép đo này:
- Mã thoát không ghi nhận được (do cách gọi `Start-Process`). Tôi kết luận thành công dựa vào file đầu ra có đúng kích thước 4000x4000. Ứng dụng thật dùng `subprocess` trong Python và sẽ đọc `returncode` đúng cách.
- Lấy mẫu mỗi 0,5 s nên có thể bỏ lỡ đỉnh ngắn hơn. Con số 1957 MiB là mức thấp nhất của đỉnh thật.
- Mới thử một kích thước. Chưa biết ngưỡng ảnh đầu vào mà tile tự động còn đủ VRAM, và chưa thử chỉnh `-t`. Cần thử thêm ảnh 2000x2000 trở lên ở 4x (đầu ra 8000x8000) khi làm US-04.

### Đo ảnh lớn bằng engine thật (US-04, đo lại ngày 11/6/2026)
Lệnh: `-n realesrgan-x4plus -g 1`, tile tự động, mỗi ca chạy một lần. Ảnh vào là ảnh tổng hợp (dải màu), không phải ảnh chụp. Máy: RAM 16 GB, RTX 3050 Laptop 4 GB.

| Ảnh vào | Hệ số | Đầu ra | Thời gian | VRAM đỉnh | RAM trống thấp nhất |
|---|---|---|---|---|---|
| 2000x2000 | 2x | 16 MP | 57,8 s | 2532 MiB | 955 MB |
| 4000x3000 | 2x | 48 MP | 111,2 s | 1266 MiB | 2310 MB |
| 2000x2000 | 4x | 64 MP | 45,7 s | 1285 MiB | 2139 MB |
| 3000x3000 | 4x | 144 MP | 96,7 s | 1294 MiB | 3288 MB |
| 4000x3000 | 4x | 192 MP | 207,2 s | 1303 MiB | 1516 MB |

Cả 5 ca đều thoát mã 0 và đúng kích thước, không có lỗi hết VRAM. Ảnh lớn nhất là 16000x12000.

Kết luận:
- **`tile`**: giữ 0. VRAM đỉnh chỉ khoảng 1,3 GB ở mọi cỡ, nên tile tự động đủ và không cần đặt số.
- **Giới hạn thật là Pillow, không phải phần cứng.** Pillow từ chối mở ảnh trên 178.956.970 điểm ảnh (`DecompressionBombError`). Ảnh 144 MP mở được kèm cảnh báo. Ảnh 192 MP ném lỗi mà `_read_size` không bắt, nên job sẽ chạy 3,5 phút rồi báo lỗi chung.
- **`max_output_pixels = 150000000`** (150 MP), thấp hơn ngưỡng Pillow. Ảnh 4000x3000 ở 4x (192 MP) sẽ bị chặn trước khi chạy và app gợi ý 2x.
- Thời gian tăng theo cả ảnh vào lẫn hệ số: cùng ảnh 4000x3000 mất 111,2 s ở 2x và 207,2 s ở 4x. Ca chậm nhất là 207,2 s, thấp hơn `engine_timeout_s = 600`. Chưa đo ảnh vào lớn hơn 12 MP nên chưa biết trần thời gian.

Hạn chế:
- Mỗi ca chỉ chạy một lần, chưa đo trên ảnh chụp thật.
- Ca 2000x2000 ở 2x có VRAM đỉnh 2532 MiB và chậm bất thường (57,8 s). Lúc đó tôi đang mở thử app song song, nhưng chưa xác nhận đó là nguyên nhân.
- RAM trống thấp nhất 955 MB ở ca đầu, cũng trùng lúc mở app thử.
- Lấy mẫu mỗi 0,5 s nên có thể bỏ lỡ đỉnh ngắn hơn.

### Chưa kiểm chứng
- **Ảnh lớn và giới hạn 4 GB VRAM** (US-04): đã đo, xem mục "Đo ảnh lớn bằng engine thật" ở trên. Còn thiếu ảnh chụp thật và nhiều lần chạy.
- **Ngưỡng tốc độ** (60 giây cho ảnh 1 megapixel ở 4x): một lần đo cho 16,5 s trên ảnh tổng hợp. Chưa đo trên ảnh chụp thật và chưa lặp lại nhiều lần.
- **Chất lượng nhìn bằng mắt** của model ảnh thật và model anime.
- **Chạy khi ngắt mạng**: engine không cần mạng để chạy (lệnh chạy không có bước tải), nhưng tôi chưa thử ngắt mạng thật. Việc này thuộc US-03.
- **Vị trí dự án nằm trong `D:\APP\UpScale`**: đường dẫn không có dấu cách, nên chưa gặp vấn đề quoting. Nếu sau này chuyển sang đường dẫn có dấu cách hoặc ký tự Unicode, cần thử lại.

## D-02: Giao diện = CustomTkinter (đề xuất, chưa cài)
Lý do: Tkinter 8.6 chạy được trên Python 3.11.9, và CustomTkinter cho giao diện hiện đại mà không cần framework nặng. Chưa cài thử `customtkinter` và `Pillow`. Sẽ kiểm tra khi bắt đầu US-02.

## D-03: Phiên bản Python = 3.11.9
Dùng `python` (3.11.9) đã xác nhận có pip và Tkinter. Lệnh `py` mặc định trỏ tới 3.14, nên mọi lệnh trong hướng dẫn phải dùng `python` hoặc `py -3.11`, không dùng `py` trần.
