# PRD: UpScale - Ứng dụng tăng độ phân giải ảnh bằng AI chạy local
**Status**: Draft  **Version**: 0.1  **Last Updated**: 11/06/2026
**Author**: Product Manager + Sprint Prioritizer (agency)  **Người dùng mục tiêu**: Cá nhân (1 người)

---

## 1. Core Problem

**Press release 1 câu**: UpScale giúp bạn phóng ảnh nhỏ lên 2x hoặc 4x sắc nét ngay trên máy của mình, không upload ảnh, không tài khoản, chỉ 3 bước: chọn ảnh, chọn hệ số, bấm Upscale.

**Vấn đề**: Bạn có ảnh độ phân giải thấp (ảnh cũ, ảnh tải về, ảnh chụp nhỏ) và cần phóng to mà không bị mờ hay vỡ hạt.
- Phóng to bằng công cụ thường (nội suy) cho ảnh mờ.
- Dịch vụ upscale online yêu cầu upload ảnh lên server, thường giới hạn số lần, dung lượng hoặc thu phí.
- Công cụ AI mã nguồn mở thường là dòng lệnh, cần tự cài môi trường, khó dùng hằng ngày.

**Bằng chứng (nói thẳng)**: Hiện chỉ có một nguồn là nhu cầu của chính bạn (n=1). Chưa có dữ liệu hành vi hay phỏng vấn nào khác. Với dự án cá nhân thì đủ để bắt đầu, nhưng các giả định bên dưới vẫn cần kiểm chứng bằng bản mẫu.

---

## 2. Goals & Success Metrics

| Goal | Metric | Target | Thời điểm đo |
|------|--------|--------|--------------|
| Dùng được không cần dòng lệnh | Hoàn thành luồng chọn ảnh, upscale, lưu qua giao diện | 100% | Cuối Sprint 1 |
| Riêng tư | Số kết nối mạng khi xử lý | 0 (kết quả vẫn ra khi ngắt mạng) | Cuối Sprint 1 |
| Ổn định | Bộ ảnh test 5 ảnh (có 1 ảnh lớn) không crash | 5/5 | Cuối Sprint 1 |
| Tốc độ (tạm thời) | Ảnh khoảng 1 megapixel, 4x, trên GPU của bạn | <= 60 giây | Chốt lại sau spike ở Sprint 1 |
| Giá trị thực | Số lần bạn tự dùng trong 2 tuần sau Sprint 1 | >= 3 lần, kết quả rõ hơn nội suy thường | 2 tuần sau Sprint 1 |

Ghi chú: chỉ số tốc độ là ngưỡng tạm vì chưa biết GPU của bạn. Chưa có baseline.

---

## 3. MVP Features (MoSCoW)

| Mức | Tính năng | Lý do |
|-----|-----------|-------|
| Must | Chọn 1 ảnh PNG/JPG từ máy | Lõi của luồng sử dụng |
| Must | Upscale 2x / 4x bằng model AI chạy local | Giá trị cốt lõi |
| Must | Lưu kết quả cạnh file gốc, không ghi đè | Tránh mất dữ liệu |
| Must | Hiển thị trạng thái đang xử lý, giao diện không bị đơ | Thiếu phản hồi thì app trông như bị treo |
| Must | Chạy hoàn toàn offline | Lý do chính để làm bản local |
| Must | Xử lý ảnh lớn an toàn (tile hoặc chặn trước), không crash | Hết VRAM là lỗi dễ gặp nhất |
| Must | Thông báo lỗi dễ hiểu và ghi log | Dễ tự sửa lỗi |
| Should | Chọn model Ảnh thật / Anime | Chất lượng khác nhau theo loại ảnh |
| Should | Xem trước ảnh gốc và ảnh kết quả cạnh nhau | Giúp đánh giá kết quả |
| Should | Xóa nền ảnh (PNG trong suốt), chạy local trên CPU | Nhu cầu thực tế; đã có mã ở Sprint 1, xem US-09 |
| Should (Sprint 2) | Xử lý hàng loạt cả thư mục | Tiện, nhưng không cần để chứng minh giá trị |

## 4. Non-Goals (không làm ở MVP)
- Upscale video.
- Tài khoản, đăng nhập, đồng bộ cloud, bất kỳ dịch vụ online nào.
- Khử nhiễu, phục hồi khuôn mặt, tô màu, các chỉnh sửa ảnh khác ngoài xóa nền.
- Lịch sử xử lý, cài đặt nâng cao, đa ngôn ngữ.
- Bản mobile, bản web, cài đặt dạng installer.
- Huấn luyện hay tinh chỉnh model.

---

## 5. Giải pháp đề xuất và quyết định mở

**Hướng kỹ thuật mặc định (đề xuất, chốt ở Task 1 của Sprint 1)**: gọi engine Real-ESRGAN dạng ncnn-vulkan qua tiến trình con, bọc bằng giao diện Python/CustomTkinter (theme tối/sáng, bo góc, bố cục một màn hình).
- Vì sao dùng CustomTkinter thay vì Tkinter thuần: bạn yêu cầu giao diện đẹp và hiện đại, Tkinter thuần trông cũ. CustomTkinter vẫn chạy trên Tkinter, thêm 2 thư viện (`customtkinter`, `Pillow`) nhưng không cần dựng web hay Qt. Chưa cài thử, sẽ xác nhận ở Task 1.
- Vì sao dùng ncnn-vulkan: không cần cài PyTorch hay CUDA, chạy trên GPU hỗ trợ Vulkan, ít phụ thuộc.
- Đánh đổi: ít kiểm soát hơn so với dùng PyTorch trực tiếp, tiến trình phải đọc qua output của tiến trình con.
- Chưa kiểm chứng: engine, model, giấy phép và khả năng chạy trên máy của bạn. Spike ở Sprint 1 sẽ xác nhận. Nếu không đạt thì phương án dự phòng là Real-ESRGAN bản PyTorch.

**Câu hỏi mở (cần trả lời trước hoặc trong ngày 1 của Sprint 1)**
- [x] GPU và VRAM của máy bạn là gì? Trả lời: RTX 3050 4GB (bạn tự khai, chưa xác nhận bằng `nvidia-smi`). 4GB VRAM là mức thấp, nên bắt buộc dùng tile và giới hạn kích thước đầu ra. Driver và hỗ trợ Vulkan chưa kiểm tra.
- [x] Ảnh bạn hay xử lý là loại nào và kích thước thường gặp? Trả lời: PNG, JPG và các định dạng khác. Chưa rõ kích thước thường gặp, và chưa rõ định dạng "khác" gồm những gì (WebP, BMP?). MVP chỉ cam kết PNG/JPG, định dạng khác ghi vào backlog nếu bạn cần.
- [x] Bạn cần 2x, 4x hay cả hai? Trả lời: cả hai.
- [x] Giao diện cửa sổ hay dòng lệnh? Trả lời: cửa sổ, trực quan, dễ dùng, đẹp và hiện đại.
- [ ] Giấy phép của engine và file model có cho phép dùng như dự định không? - Owner: dev, Task 1

## 6. Rủi ro

| Rủi ro | Khả năng | Tác động | Giảm thiểu |
|--------|----------|----------|------------|
| GPU không hỗ trợ Vulkan hoặc quá yếu | Thấp đến trung bình (RTX 3050 thường hỗ trợ Vulkan, chưa kiểm chứng trên máy) | Cao | Spike ngày 1, có phương án CPU hoặc PyTorch |
| Hết VRAM với ảnh lớn (chỉ 4GB VRAM) | Cao | Trung bình | Dùng tile nhỏ, kiểm tra kích thước đầu ra trước khi chạy, 4x chậm hơn 2x |
| Giao diện hiện đại làm US-02 vượt 5 điểm | Trung bình | Trung bình | Dựng khung chạy được trước, chỉnh giao diện sau, đo lại ở cuối ngày 3 |
| Không đọc được tiến độ từ engine | Trung bình | Thấp | Chỉ hiển thị trạng thái "đang xử lý", không hứa phần trăm |
| Scope phình ra (batch, preview, model...) | Cao | Trung bình | Chỉ cam kết Must trong Sprint 1, mọi yêu cầu mới ghi vào backlog |

---

## 7. User Stories và Acceptance Criteria

### US-01 (Must, 3 điểm) - Engine chạy được trên máy
Là người dùng, tôi muốn engine AI chạy được trên máy của mình để có nền tảng cho app và biết giới hạn phần cứng.
- [ ] Given engine và model đã nằm trong thư mục dự án, when chạy upscale một ảnh mẫu, then ra file ảnh có kích thước bằng ảnh gốc nhân hệ số scale.
- [ ] Given máy có GPU hỗ trợ Vulkan, when chạy, then engine dùng GPU (xác nhận qua log hoặc Task Manager) và ghi lại thời gian xử lý.
- [ ] Given máy không dùng được GPU, when chạy, then kết quả (lỗi hoặc chạy CPU) được ghi lại để quyết định phạm vi hỗ trợ.
- [ ] Quyết định stack và giấy phép được ghi vào `docs/`.

### US-02 (Must, 5 điểm) - Upscale một ảnh qua giao diện
Là người dùng, tôi muốn chọn ảnh, chọn hệ số và bấm một nút để nhận ảnh đã phóng to, để không phải dùng dòng lệnh.
- [ ] Given mở app, when bấm "Chọn ảnh" và chọn file PNG hoặc JPG, then hiển thị tên file và kích thước gốc (rộng x cao).
- [ ] Given đã chọn ảnh, when chọn 2x hoặc 4x rồi bấm "Upscale", then giao diện hiển thị trạng thái đang xử lý, cửa sổ vẫn phản hồi, nút Upscale bị khóa đến khi xong.
- [ ] Given xử lý xong, then ảnh lưu cạnh file gốc với tên `<tên>_x<scale>.png`, kích thước đúng bằng gốc nhân scale, app hiển thị đường dẫn và nút mở thư mục chứa file.
- [ ] Given file đích đã tồn tại, then không ghi đè mà thêm hậu tố số.
- [ ] Given xử lý, then file gốc không bị thay đổi.
- [ ] Given mở app, then giao diện dùng CustomTkinter với theme tối/sáng, bảng màu và font nhất quán, không còn widget Tk mặc định kiểu cũ, và mọi nút bấm được bằng bàn phím.

### US-03 (Must, 1 điểm) - Chạy offline, riêng tư
Là người dùng, tôi muốn ảnh không rời khỏi máy để yên tâm xử lý ảnh cá nhân.
- [ ] Given ngắt mạng (tắt Wi-Fi hoặc rút cáp), when upscale, then kết quả vẫn ra bình thường.
- [ ] Given app đang chạy, then mã nguồn không có lời gọi mạng nào và model nằm sẵn trong thư mục dự án, không tải khi chạy.

### US-04 (Must, 2 điểm) - Ảnh lớn không làm app crash
Là người dùng, tôi muốn app xử lý được ảnh lớn hoặc báo rõ giới hạn, để không bị treo máy.
- [ ] Given ảnh lớn (ví dụ 4000x3000), when upscale, then app hoàn thành bằng cách xử lý theo tile hoặc báo lỗi rõ ràng, không crash, không treo máy.
- [ ] Given kích thước đầu ra vượt giới hạn do spike xác định, when bấm Upscale, then app chặn trước khi xử lý và gợi ý dùng hệ số nhỏ hơn.

### US-05 (Must, 2 điểm) - Lỗi dễ hiểu
Là người dùng, tôi muốn biết chuyện gì sai và cách xử lý, để không phải đọc stack trace.
- [ ] Given file không phải ảnh hoặc bị hỏng, then hiện thông báo "Không đọc được ảnh", không hiện stack trace.
- [ ] Given thiếu engine hoặc model, then thông báo nêu đường dẫn đang thiếu.
- [ ] Given engine thoát với lỗi (ví dụ hết VRAM), then thông báo kèm gợi ý xử lý.
- [ ] Mọi lỗi được ghi vào `logs/app.log`, và sau lỗi app vẫn dùng tiếp được.

### US-06 (Should, 2 điểm) - Chọn model Ảnh thật / Anime
- [ ] Given màn hình chính, then có lựa chọn "Ảnh thật" (mặc định) và "Anime".
- [ ] Given chọn một model, when upscale, then log ghi đúng model đã dùng.

### US-07 (Should, 5 điểm, dự kiến Sprint 2) - Xử lý cả thư mục
- [ ] Given chọn một thư mục, when bấm xử lý, then lần lượt xử lý mọi file PNG/JPG và hiển thị tiến độ i/N.
- [ ] Given một ảnh bị lỗi, then lô vẫn chạy tiếp và cuối cùng hiển thị tổng số thành công và thất bại.

### US-08 (Should, 3 điểm) - Xem trước và sau
- [ ] Given xử lý xong, then hiển thị ảnh gốc và ảnh kết quả cạnh nhau, có thể phóng to.
- [ ] Given ảnh kết quả rất lớn, when mở xem trước, then giao diện không bị đơ.

### US-09 (Should, 3 điểm) - Xóa nền ảnh
Là người dùng, tôi muốn xóa nền một ảnh ngay trên máy để dùng ảnh trong thiết kế mà không upload đi đâu.
- [x] Given ảnh PNG/JPG đã chọn, when chọn chế độ "Xóa nền" và bấm nút, then app không hiện lựa chọn hệ số phóng to hay loại ảnh, và nút ghi "Xóa nền".
- [x] Given xử lý xong, then lưu `<tên>_nobg.png` cạnh ảnh gốc, đúng kích thước gốc, có alpha; file gốc không đổi; file đích có sẵn thì thêm hậu tố số.
- [x] Given ảnh gốc đã có vùng trong suốt, then vùng đó vẫn trong suốt.
- [x] Given thiếu model hoặc thiếu thư viện, then thông báo nêu cách khắc phục, app vẫn dùng tiếp được ở chế độ còn lại.
- [x] Chạy offline, CPU, không cần GPU.
- Hạn chế đã biết: ảnh anime/tranh vẽ có nền phẳng chưa xóa sạch nền; viền hơi mềm với ảnh lớn. Xem `DECISIONS.md` D-06.
- Chưa đạt: chưa ai thao tác GUI bằng tay (kiểm tra tự động: 15/15 mục).

### Bảng ưu tiên

| Story | Mức | Giá trị | Công sức (điểm) | Sprint |
|-------|-----|---------|-----------------|--------|
| US-01 Engine chạy được | Must | Rất cao (mở khóa mọi thứ) | 3 | 1 |
| US-02 Upscale qua giao diện | Must | Rất cao | 5 | 1 |
| US-04 Ảnh lớn | Must | Cao | 2 | 1 |
| US-05 Lỗi dễ hiểu | Must | Cao | 2 | 1 |
| US-03 Offline | Must | Cao | 1 | 1 |
| US-06 Chọn model | Should | Trung bình | 2 | 1 (stretch) |
| US-08 Xem trước/sau | Should | Trung bình | 3 | 1 (stretch) hoặc 2 |
| US-07 Cả thư mục | Should | Trung bình | 5 | 2 |
| US-09 Xóa nền | Should | Trung bình | 3 | 1 (đã có mã) |

Điểm là ước lượng thô, sẽ hiệu chỉnh sau Sprint 1 khi có velocity thực tế.
