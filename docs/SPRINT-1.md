# Sprint 1 - Bản mẫu chạy được
**Thời lượng**: 1 tuần (5 ngày làm việc)  **Cập nhật**: 11/06/2026

## Sprint Goal
Cuối Sprint 1, bạn chạy app trên máy mình, chọn một ảnh, bấm Upscale 2x hoặc 4x khi đang ngắt mạng, và nhận ảnh đã lưu cạnh file gốc.

**Tiêu chí thành công**: bộ ảnh test 5 ảnh (có 1 ảnh lớn) chạy xong 5/5, không crash, không có kết nối mạng.

## Giả định về năng lực (cần bạn xác nhận)
- 1 người phát triển, khoảng 15 đến 20 giờ hiệu dụng trong tuần.
- Năng lực ước tính: 16 điểm. Trừ 15% đệm cho rủi ro, cam kết 13 điểm.
- Chưa có velocity lịch sử. Sprint 1 là mốc để hiệu chỉnh cho các sprint sau.

## Cam kết (13 điểm)

| Thứ tự | Story | Điểm | Phụ thuộc |
|--------|-------|------|-----------|
| 1 | US-01 Engine chạy được | 3 | Trả lời câu hỏi mở về GPU |
| 2 | US-02 Upscale qua giao diện | 5 | US-01 |
| 3 | US-04 Ảnh lớn | 2 | US-02 |
| 4 | US-05 Lỗi dễ hiểu | 2 | US-02 |
| 5 | US-03 Offline | 1 | US-02 |

## Stretch (chỉ làm khi cam kết đã xong)
1. US-06 Chọn model Ảnh thật / Anime (2 điểm)
2. US-08 Xem trước và sau (3 điểm)

## Không làm trong Sprint 1
US-07 (cả thư mục), mọi mục trong Non-Goals của PRD. Yêu cầu mới phát sinh giữa sprint được ghi vào backlog và quyết định ở Sprint 2, không nhận âm thầm.

## Kế hoạch theo ngày và task

**Ngày 1 - Spike (US-01)**
- Câu hỏi mở đã trả lời: RTX 3050 4GB, ảnh PNG/JPG, cần 2x và 4x, giao diện cửa sổ đẹp hiện đại. Còn phải xác nhận trên máy bằng `nvidia-smi` và kiểm tra Vulkan.
- Tải engine và model vào thư mục dự án, kiểm tra giấy phép.
- Chạy thử trên 1 ảnh mẫu, ghi lại thời gian và việc có dùng GPU hay không.
- Chốt stack, ghi quyết định vào `docs/`.
- **Cổng quyết định cuối ngày 1**: nếu engine không chạy được trên GPU, chuyển sang phương án dự phòng (Real-ESRGAN bản PyTorch hoặc chạy CPU) và báo lại ngay, vì có thể cần giảm phạm vi của sprint.
- **Trạng thái (11/06/2026)**: spike xong, cổng được thông qua. Engine chạy trên RTX 3050 (5,07 s cho 4x ảnh 220x220). Chi tiết và các điểm chưa kiểm chứng ở `docs/DECISIONS.md`. Còn hai việc cần thử trước khi làm US-02: `realesrgan-x4plus -s 2` cho ảnh thật, và một ảnh lớn để tìm tile an toàn với 4 GB VRAM.

**Ngày 2-3 - Luồng chính (US-02)**
- Khung dự án, cấu trúc thư mục, file cấu hình đường dẫn engine và model.
- Hàm gọi engine qua tiến trình con, chạy ở luồng riêng để giao diện không đơ.
- Giao diện: chọn ảnh, chọn 2x/4x, nút Upscale, trạng thái, đường dẫn kết quả.
- Đặt tên file đầu ra, tránh ghi đè.
- Test cơ bản cho phần đặt tên file và tính kích thước đầu ra.

**Ngày 4 - Độ bền (US-04, US-05)**
- Kiểm tra kích thước đầu ra trước khi chạy, dùng tile cho ảnh lớn.
- Bắt lỗi quanh việc đọc ảnh, thiếu engine hoặc model, engine thoát lỗi.
- Ghi log vào `logs/app.log`.

**Ngày 5 - Nghiệm thu (US-03) và demo**
- Kiểm tra offline: ngắt mạng, chạy bộ ảnh test.
- Chạy toàn bộ test, rà soát không còn TODO hay placeholder.
- Demo theo checklist bên dưới, họp retro ngắn, làm stretch nếu còn thời gian.

## Definition of Done
- Chạy được trên máy của bạn từ đầu đến cuối, không cần chỉnh tay.
- Mọi Acceptance Criteria của story đều đạt.
- Test và kiểm tra cú pháp chạy xong, không lỗi.
- Không còn TODO hay code dở dang. Lỗi được bắt bằng try/catch an toàn.
- Hướng dẫn cài và chạy ngắn gọn trong `README.md`.

## Checklist demo cuối sprint
- [ ] Mở app, chọn ảnh, thấy kích thước gốc.
- [ ] Upscale 2x và 4x, kích thước ảnh kết quả đúng.
- [ ] Giao diện không đơ khi đang xử lý.
- [ ] Ngắt mạng, vẫn upscale được.
- [ ] Ảnh lớn không làm crash.
- [ ] Chọn file không phải ảnh, thấy thông báo lỗi dễ hiểu.
- [ ] File gốc không bị đổi, file đích không bị ghi đè.

## Rủi ro của sprint

| Rủi ro | Dấu hiệu sớm | Hành động |
|--------|--------------|-----------|
| Engine không chạy trên GPU | Lỗi ở spike ngày 1 | Dùng cổng quyết định ngày 1 |
| Tiến độ trễ ở US-02 | Hết ngày 3 chưa có luồng chạy hết | Bỏ US-04 phần tile, chỉ chặn trước kích thước |
| Thêm tính năng giữa sprint | Có yêu cầu mới | Ghi backlog, không nhận vào sprint |
| Giao diện đẹp hiện đại làm US-02 vượt 5 điểm | Hết ngày 3 giao diện chưa xong luồng chính | Làm luồng chạy được trước với giao diện cơ bản, chỉnh theme sau; nếu vẫn trễ thì bỏ stretch |
| Chỉ 4GB VRAM, 4x dễ hết bộ nhớ | Engine báo lỗi bộ nhớ ở spike | Giảm kích thước tile, đo ngưỡng ảnh đầu ra tối đa cho US-04 |

## Sau Sprint 1
Sprint 2 dự kiến: US-07 (cả thư mục), US-08 nếu chưa xong, rồi đóng gói để dùng hằng ngày. Thứ tự này sẽ xem lại dựa trên velocity thực tế và việc bạn thật sự dùng app.
