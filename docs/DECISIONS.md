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
`.venv` đã được tạo lại bằng `py -3.11 -m venv .venv` (trước đó là 3.14.6, chưa cài thư viện).

## D-04: Engine crash khi đường dẫn ĐẦU RA có ký tự Unicode (đã sửa)
**Triệu chứng**: log 06/11 17:39 ghi `ENGINE_FAILED returncode=3221226505` (0xC0000409) với ảnh trong thư mục `...\_ĐẢNG\Chu Ky\`.

**Tái hiện bằng engine thật** (RTX 3050, `-g 1`):
| Đường dẫn vào | Đường dẫn ra | Kết quả |
|---|---|---|
| ASCII | ASCII | exit 0 |
| Unicode | ASCII | exit 0 |
| ASCII | Unicode | **exit 3221226505, không có file** |
Ảnh RGB hay RGBA không ảnh hưởng. Chỉ đường dẫn đầu ra là nguyên nhân.

**Cách sửa** (`UpscaleService._ascii_scratch`): khi file tạm cạnh ảnh gốc có ký tự không phải ASCII, engine ghi vào `%TEMP%\upscale_<job>.png`, rồi service chuyển file về cạnh ảnh gốc và đổi tên như cũ. Nếu cả `%TEMP%` cũng không phải ASCII (tên người dùng có dấu) thì báo lỗi rõ ràng thay vì để engine crash. Đã thử lại bằng engine thật trên thư mục `_ĐẢNG\Chu Ky`: ra 880x880, file kết quả nằm cạnh ảnh gốc, không còn file tạm.

**Chưa kiểm chứng**: trường hợp `%TEMP%` có ký tự Unicode (nhánh báo lỗi chỉ có logic, chưa chạy với máy như vậy).

## D-05: Chế độ 2x chạy engine ở 4x rồi thu nhỏ (đã sửa)
**Phát hiện khi xem ảnh bằng mắt** (mục "Chất lượng nhìn bằng mắt" còn mở ở D-01): `-n realesrgan-x4plus -s 2` trả đúng kích thước nhưng nội dung hỏng. Ảnh bãi biển 256x256 chỉ còn một góc phóng to rồi lặp lại, ảnh anime 220x220 cũng bị cắt và nhân đôi. Cả hai model (ảnh thật và anime) đều bị. Nên kết luận ở D-01 mục 4 ("2x chạy được") chỉ đúng về kích thước, không đúng về nội dung.

**Cách sửa** (`UpscaleService._run`): luôn gọi engine với `-s 4`, riêng 2x thì thu nhỏ kết quả bằng Pillow LANCZOS về đúng kích thước. Đo PSNR so với ảnh gốc phóng 2x bằng LANCZOS:
| Ảnh | `-s 2` (hỏng) | `-s 4` rồi thu về 2x |
|---|---|---|
| input.jpg | 25,0 dB | 30,0 dB |
| input2.jpg | 25,6 dB | 32,6 dB |
Chạy qua service sau khi sửa: 30,0 / 29,7 dB (input.jpg, ảnh thật / anime) và 32,6 / 33,0 dB (input2.jpg). PSNR chỉ là chỉ báo thô vì ảnh tham chiếu là phép nội suy, không phải ảnh chuẩn.

**Hệ quả**: 2x tốn thời gian và VRAM như 4x. Giới hạn `max_output_pixels` giờ áp dụng cho ảnh 4x trung gian, nên ảnh lớn bị chặn ở 2x sớm hơn trước (thông báo riêng, không còn gợi ý "Chọn 2x" vì đang ở 2x).

**Chưa kiểm chứng**: chưa so chất lượng 2x giữa model ảnh thật và anime bằng mắt trên ảnh chụp thật; chỉ xem hai ảnh mẫu của engine.

## Nghiệm thu Sprint 1 (06/11/2026, engine thật, RTX 3050)
Chạy `UpscaleService` thật (không qua GUI) với 5 ảnh:
| Ảnh | Vào | Hệ số | Ra | Thời gian | Kết quả |
|---|---|---|---|---|---|
| input.jpg | 220x220 | 4x | 880x880 | 3,2 s | đạt |
| input2.jpg | 256x256 | 2x | 512x512 | 2,8 s | đạt |
| s1000.png (tổng hợp) | 1000x1000 | 4x | 4000x4000 | 11,8 s | đạt |
| s1672.png (tổng hợp) | 1672x941 | 2x | 3344x1882 | 16,2 s | đạt |
| big3000.png (tổng hợp, ảnh lớn) | 3000x2000 | 2x | 6000x4000 | 55,0 s | đạt |
Cả 5 ảnh đều đúng kích thước, file gốc không đổi (so SHA256), chạy lại ảnh đầu cho `input_x4_2.png` không ghi đè. Lưu ý: số liệu 2x ở bảng này lấy **trước** khi sửa D-05 (lúc đó 2x còn chạy `-s 2`). Đo lại sau D-05 chỉ với ảnh lớn: 3000x2000 ở 2x mất 66,2 s (đầu ra 6000x4000), ở 4x mất 65,5 s (12000x8000), trên ảnh nhiễu tổng hợp. Bốn ảnh còn lại chưa đo lại.
Ở 4x ảnh này là 96 MP, Pillow in `DecompressionBombWarning` (ngưỡng cảnh báo 89,5 MP) nhưng vẫn mở và lưu bình thường; chỉ ngưỡng lỗi (khoảng 179 MP) mới chặn, và `max_output_pixels=150000000` nằm dưới ngưỡng đó.

**Offline**: trong lúc chạy, Python bị chặn `socket.connect` và `getaddrinfo` (0 lần cố kết nối), và tôi lấy mẫu 90 lần tiến trình engine bằng `Get-NetTCPConnection`/`Get-NetUDPEndpoint` (0 kết nối). Đây **không phải** thử ngắt mạng thật (Wi-Fi vẫn bật), nên US-03 chỉ ở mức bằng chứng gián tiếp.

**Ảnh chụp thật**: bộ này dùng ảnh mẫu của engine và ảnh tổng hợp, chưa có ảnh chụp thật nhiều chi tiết.

**GUI**: `python run.py` sống sau 8 giây. `pyinstaller UpScale.spec` build xong và `scripts/smoke_exe.ps1` báo chạy 8 giây và ghi được `logs\app.log`. Chưa ai thao tác GUI để chọn ảnh và bấm Upscale.

## Bất thường trong log chưa giải thích hết
- **06/11 10:18 đến 10:23, job smoke 880x880 mất 318,6 s**: hiện cùng ảnh chạy 2,5 s qua `UpscaleService` (hai lần liên tiếp, cùng `config.toml`). Chưa tái hiện được 318 s, nên nguyên nhân chưa biết (nghi tranh chấp GPU lúc đó, chưa xác nhận).
- **06/11 15:34, job ảnh `01a19a93-....png` (1672x941) không có dòng "xong" hay "lỗi"**: file tạm `.01a19a93-...x4.ae6fce24.tmp.png` còn nằm trong `Downloads`, đọc được đủ 6688x3764, sửa lần cuối 15:34:53. Nghĩa là engine chạy xong sau khoảng 38 s rồi tiến trình app dừng trước khi đổi tên và ghi log. Chưa xác định vì sao (nghi app bị đóng đột ngột). File này có thể chính là kết quả hoàn chỉnh; tôi **không xóa**. App hiện chưa dọn file tạm mồ côi khi khởi động (ghi vào backlog).

## D-06: Xóa nền ảnh bằng U²-Net qua onnxruntime, module `bgremoval` độc lập (06/11/2026)
**Phạm vi**: PRD ghi "chỉnh sửa ảnh" trong Non-Goals. Tính năng này do người dùng yêu cầu trực tiếp, nên là mở rộng phạm vi có chủ đích, chưa sửa PRD.

**Vị trí và ranh giới**: `src/upscale/bgremoval/` là gói riêng, cùng dạng với `UpscaleService` để dùng lại `EventBridge`, thanh tiến độ, hộp thoại hủy và `UpscaleError`. Nó chỉ import `domain` và `infra` (cho `JobEvent`, `ErrorCode`, `Config`, `inspect_image`, `check_output_limit`). `UpscaleService`, `engine_runner` và `domain` không bị sửa. Chỗ nối duy nhất là `ui/app.py` (thêm công tắc "Phóng to / Xóa nền") và một hàm `bg_done_notice` trong `ui/presenter.py`.
| File | Việc |
|---|---|
| `matting.py` | Tiền xử lý 320x320, đổi đầu ra model thành mặt nạ, ghép alpha. Không I/O |
| `session.py` | Duy nhất biết về onnxruntime. Kiểm SHA256 file model rồi mới nạp |
| `rules.py` | Đặt tên `<tên>_nobg.png`, không ghi đè |
| `service.py` | Điều phối một job, phát `JobEvent`, hủy giữa các bước |

**Chọn model** (đo trên CPU, cùng bước tiền xử lý, cùng ảnh):
| Ảnh | u2netp (4,6 MB) | silueta (44 MB) | u2net (176 MB) |
|---|---|---|---|
| Ảnh người (girl-1) | xóa sót, vùng chân bị mờ | tốt | tốt |
| Hổ, ô tô | gần như tương đương | tương đương | tương đương |
| Ảnh anime 220x220 | viền nhòe, nhiều vùng alpha lưng chừng | 85% alpha lưng chừng | 76% alpha lưng chừng |
Chọn **u2net** làm mặc định vì không kém model nào trên ảnh thật và cho viền tốt nhất trên ảnh người. Tốc độ đo trên CPU: 0,16 đến 0,5 s cho ảnh nhỏ sau lần nạp đầu (nạp model và tính SHA256 mất khoảng 1,6 đến 2,2 s ở job đầu), 6000x4000 mất 7,3 đến 9,1 s.

**Hạn chế đã thấy, chưa khắc phục**
- Ảnh anime/vẽ tay có nền phẳng: cả ba model đều cho mặt nạ mềm (76 đến 85% điểm ảnh có alpha lưng chừng), nên nền không bị xóa sạch. U²-Net học từ ảnh thật và đối tượng nổi bật, không phải ảnh vẽ. Chỉ đo trên một ảnh anime.
- Mặt nạ chạy ở 320x320 rồi phóng lên, nên với ảnh lớn đường viền mềm và có thể ăn vào hoặc lố ra vài điểm ảnh (thấy ở viền chân hổ: có vệt hồng nhạt khi ghép lên nền hồng đậm). Không có bước làm sắc viền (alpha matting).
- Chưa có quy tắc ngưỡng: kết quả là alpha liên tục, không nhị phân hóa.

**Giấy phép**: mã U-2-Net là Apache 2.0 (đã đối chiếu file LICENSE trên GitHub). File `u2net.onnx` tải từ rembg release v0.0.0, giấy phép riêng của file trọng số này **chưa được xác nhận**.

**Nguồn và hash** (hash do tôi tính sau khi tải, không có hash công bố để đối chiếu): `u2net.onnx`, 175.997.641 byte, SHA256 `8D10D2F3BB75AE3B6D527C77944FC5E7DCD94B29809D47A739A7A728A912B491`. Service từ chối nạp file khác hash này.

**Phụ thuộc mới**: `numpy==2.4.6`, `onnxruntime==1.31.1` (chỉ CPUExecutionProvider, không GPU). Build PyInstaller bản có hai thư viện này tăng `dist/UpScale` lên 108 MB. Smoke test `.exe` đạt, nhưng **chưa thử xóa nền trong `.exe`** (cần model đặt cạnh exe).

**Chưa kiểm chứng**: GUI ở chế độ xóa nền chưa ai thao tác bằng tay; chưa thử trên máy không có AVX hoặc CPU rất cũ; chưa đo bộ nhớ đỉnh với ảnh rất lớn.
