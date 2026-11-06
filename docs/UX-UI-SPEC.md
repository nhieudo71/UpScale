# Đặc tả UX/UI - UpScale

**Cập nhật**: 11/06/2026  **Vai trò**: UX Architect + UI Designer (agency)
**Căn cứ**: `docs/PRD.md` (US-02 đến US-06, US-08), `docs/ARCHITECTURE.md` (mã lỗi, sự kiện job)

**Phạm vi**: ứng dụng desktop một cửa sổ, một người dùng. Mọi chỉ số tương phản trong tài liệu này do tôi tính bằng công thức WCAG 2.x trên máy, không lấy từ công cụ bên thứ ba. Các điểm chưa kiểm chứng nằm ở mục 5.

## 1. User Flow

Mục tiêu chính: chọn ảnh, chọn hệ số, bấm Upscale, nhận ảnh đã lưu. PRD cam kết 3 bước.

```
Mở app
  |
  v
[Kiểm tra engine + model] --thiếu--> M1 Màn hình "Thiếu engine" (nêu đường dẫn) --> Thoát
  | đủ
  v
S0 Trống: "Chọn ảnh" -----------------------------+
  | chọn file                                      |
  v                                                |
[Pillow đọc ảnh] --lỗi--> E1 "Không đọc được ảnh" -+ (quay lại S0, app dùng tiếp)
  | ok
  v
S1 Đã chọn ảnh: tên, rộng x cao, [2x | 4x], [Ảnh thật | Anime]
  |  bấm Upscale
  v
[Kiểm tra kích thước đầu ra] --vượt giới hạn--> E2 chặn trước, gợi ý 2x (ở lại S1)
  | ok
  v
S2 Đang xử lý: thanh tiến độ %, nút Hủy, các điều khiển khác bị khóa
  |--- hủy ---------> S1 (không để lại file dở)
  |--- engine lỗi ---> E3 lỗi kèm gợi ý, [Thử lại] (về S1)
  | xong
  v
S3 Hoàn tất: đường dẫn, kích thước kết quả, [Mở thư mục], [Upscale ảnh khác]
  | "Upscale ảnh khác"
  +--> S0
```

**Quyết định UX**
| Quyết định | Lý do |
|---|---|
| Một màn hình, bốn trạng thái (S0 đến S3), không có trang phụ | Đúng PRD "bố cục một màn hình", giảm điều hướng |
| Hệ số 2x và 4x là nhóm nút chọn một, mặc định 4x | Chỉ có hai giá trị, nút phân đoạn nhanh hơn danh sách thả xuống |
| Model mặc định "Ảnh thật" | Theo US-06 |
| Khi đang xử lý, khóa chọn ảnh, hệ số, model và nút Upscale. Chỉ nút Hủy dùng được | Tránh đổi tham số giữa chừng, khớp US-02 |
| Lỗi hiện ngay tại chỗ (thẻ lỗi trong màn hình), không dùng hộp thoại | Không chặn người dùng, đọc được cùng lúc với ảnh đã chọn |
| Sau lỗi luôn về được S1 hoặc S0 | US-05: "sau lỗi app vẫn dùng tiếp được" |
| Không có kéo thả ảnh vào cửa sổ ở MVP | Tkinter không hỗ trợ sẵn, cần thêm thư viện `tkinterdnd2` ngoài stack đã chốt. Ghi vào backlog |

**Bàn phím** (US-02 yêu cầu mọi nút bấm được bằng bàn phím)
| Phím | Tác dụng |
|---|---|
| `Tab` / `Shift+Tab` | Di chuyển theo thứ tự: Chọn ảnh, 2x, 4x, model, Upscale, Mở thư mục |
| `Enter` / `Space` | Kích hoạt nút đang focus |
| `Ctrl+O` | Chọn ảnh |
| `Esc` | Hủy khi đang xử lý, đóng hộp thoại khi đang mở |

## 2. Design Tokens

Ứng dụng có hai theme, sáng và tối, và một lựa chọn "Theo hệ thống" (mặc định). Component chỉ dùng tên token, không ghi mã màu trực tiếp.

### 2.1 Màu (đã tính tương phản)

| Token | Sáng | Tối | Dùng cho |
|---|---|---|---|
| `bg` | `#F6F7F9` | `#0E1015` | Nền cửa sổ |
| `surface` | `#FFFFFF` | `#161920` | Thẻ, hộp thoại |
| `surface-alt` | `#EEF0F4` | `#1F232C` | Vùng ảnh, hàng xen kẽ, nút phụ |
| `border` | `#7A8394` | `#6B7385` | Viền ô nhập, viền nút phụ |
| `text` | `#171A21` | `#ECEEF2` | Chữ chính |
| `text-muted` | `#4A5160` | `#A7AEBC` | Chữ phụ, nhãn, gợi ý |
| `primary` | `#4338CA` | `#6E72F5` | Nút chính, mục đang chọn, focus |
| `primary-hover` | `#3730A3` | `#8084F8` | Hover nút chính |
| `on-primary` | `#FFFFFF` | `#0E1015` | Chữ trên nút chính |
| `secondary` | `#0B6370` | `#4FD1D9` | Điểm nhấn phụ, liên kết, biểu tượng thông tin |
| `secondary-bg` | `#E2F3F5` | `#12303A` | Nền thẻ thông tin |
| `danger` | `#B42318` | `#FF8A80` | Chữ và viền lỗi, nút nguy hiểm |
| `danger-bg` | `#FDECEA` | `#3A1A19` | Nền thẻ lỗi |
| `on-danger` | `#FFFFFF` | `#0E1015` | Chữ trên nút nguy hiểm |
| `success` | `#146C43` | `#5FD398` | Chữ và biểu tượng thành công |
| `success-bg` | `#E6F4EC` | `#16301F` | Nền thẻ thành công |
| `warning` | `#8A4B00` | `#F5B454` | Cảnh báo (ví dụ ảnh lớn) |
| `warning-bg` | `#FFF4E0` | `#33260F` | Nền thẻ cảnh báo |

**Kết quả tính tương phản** (tiêu chuẩn: chữ thường 4,5:1, thành phần giao diện 3:1)
| Cặp | Sáng | Tối |
|---|---|---|
| `text` trên `bg` / `surface` / `surface-alt` | 16,24 / 17,41 / 15,26 | 16,38 / 15,14 / 13,54 |
| `text-muted` trên `bg` / `surface` / `surface-alt` | 7,43 / 7,96 / 6,98 | 8,54 / 7,89 / 7,06 |
| `on-primary` trên `primary` / `primary-hover` | 7,90 / 9,93 | 4,88 / 5,96 |
| `primary` trên `surface` / `bg` (focus, mục chọn) | 7,90 / 7,37 | 4,51 / 4,88 |
| `border` trên `bg` / `surface` / `surface-alt` | 3,56 / 3,82 / 3,35 | 4,00 / 3,70 / 3,31 |
| `secondary` trên `surface` / `secondary-bg` | 6,92 / 6,06 | 9,59 / 7,59 |
| `danger` trên `surface` / `danger-bg` | 6,57 / 5,75 | 7,70 / 6,86 |
| `on-danger` trên `danger` | 6,57 | 8,34 |
| `success` trên `surface` / `success-bg` | 6,45 / 5,69 | 9,43 / 7,62 |
| `warning` trên `warning-bg` | 6,24 | 8,10 |

Mọi cặp trên đạt ngưỡng của loại nội dung nó dùng. Lần tính đầu tiên cho thấy `border` sáng `#8A93A3` chỉ đạt 2,89:1 trên `bg`, dưới 3:1, nên tôi đổi thành `#7A8394`.

**Quy tắc dùng màu**
- Không dùng màu làm tín hiệu duy nhất. Lỗi luôn kèm biểu tượng và chữ, thành công kèm dấu tích và chữ.
- Trạng thái vô hiệu hóa (disabled) không bắt buộc đạt tỉ lệ này theo WCAG, nhưng vẫn phải đọc được. Dùng `text-muted` trên `surface-alt`, và tôi chưa tính riêng cặp màu disabled.
- Chưa tính: màu hover của nút phụ và nút nguy hiểm, màu thanh tiến độ trên nền rãnh. Cần tính khi chọn giá trị cụ thể lúc cài đặt.

### 2.2 Typography

Font kiểm tra trên máy bằng `tkinter.font.families()`: `Segoe UI Variable Text`, `Segoe UI`, `Segoe UI Semibold` và `Consolas` đều có. `Inter` không có, nên không dùng, vì app chạy offline và không đóng gói font.

| Token | Font | Cỡ (pt) | Độ đậm | Dùng cho |
|---|---|---|---|---|
| `font-family` | `Segoe UI Variable Text`, dự phòng `Segoe UI` | - | - | Toàn bộ giao diện |
| `font-mono` | `Consolas` | - | - | Đường dẫn file, mã lỗi |
| `type-title` | `font-family` | 20 | Bold | Tên app, tiêu đề màn hình |
| `type-heading` | `font-family` | 14 | Bold | Tiêu đề thẻ, tiêu đề hộp thoại |
| `type-body` | `font-family` | 11 | Normal | Nội dung, nhãn nút |
| `type-body-strong` | `font-family` | 11 | Bold | Tên file, giá trị quan trọng |
| `type-caption` | `font-family` | 10 | Normal | Gợi ý, kích thước ảnh, thời gian |
| `type-mono` | `font-mono` | 10 | Normal | Đường dẫn, mã lỗi |

- Cỡ nhỏ nhất là 10 pt. Chưa kiểm tra bằng mắt trên màn hình thật của bạn, và chưa thử với cỡ chữ hệ thống 125% hoặc 150%.
- Máy này có DPI 96 (hệ số 100%). CustomTkinter tự co giãn theo DPI, nhưng tôi chưa kiểm tra bố cục ở các mức khác.
- Tỉ lệ cấp bậc 20 / 14 / 11 / 10, khoảng cách giữa các cấp đủ để nhìn ra thứ tự mà không cần thêm màu.

### 2.3 Khoảng cách, bo góc, viền

| Token | Giá trị | Ghi chú |
|---|---|---|
| `space-1` đến `space-6` | 4, 8, 12, 16, 24, 32 px | Lưới 4 px |
| `radius-sm` | 6 px | Ô nhập, nút phân đoạn |
| `radius-md` | 10 px | Nút, thẻ nhỏ |
| `radius-lg` | 14 px | Thẻ lớn, hộp thoại |
| `border-width` | 1 px | Viền ô nhập và nút phụ |
| `focus-ring` | 2 px, màu `primary` | Hiện khi focus bằng bàn phím |
| `control-height` | 40 px | Chiều cao tối thiểu nút và ô nhập |
| `window-min` | 760 x 560 px | Kích thước cửa sổ tối thiểu |
| `window-default` | 960 x 640 px | Kích thước mở lần đầu |

Với máy tính để bàn, chiều cao 40 px đủ cho con trỏ chuột và bàn phím. Mục tiêu cảm ứng 44 px của agent UI Designer áp dụng cho thiết bị cảm ứng, mà MVP không nhắm tới.

### 2.4 Chuyển động
- Thời lượng: 150 ms cho hover và đổi trạng thái nút.
- Thanh tiến độ cập nhật theo sự kiện `progress`, không làm mượt giả.
- Tkinter không có tùy chọn hệ thống "giảm chuyển động" sẵn. MVP không dùng hoạt ảnh nào ngoài thanh tiến độ và vòng chờ, nên không phát sinh vấn đề.

## 3. Đặc tả component

Component dựng trên CustomTkinter (`CTkButton`, `CTkSegmentedButton`, `CTkEntry`, `CTkFrame`, `CTkProgressBar`, `CTkToplevel`, `CTkScrollableFrame`). Các giá trị lấy từ mục 2. Tôi chưa cài `customtkinter`, nên chưa kiểm tra từng tham số có được thư viện hỗ trợ hay không. Việc kiểm tra thuộc đầu US-02.

**Phạm vi MVP:** màn hình Sprint 1 dùng Button, Segmented control, Input (chỉ đọc), Card, Progress và Modal xác nhận. Table chưa có màn hình nào dùng, vì lịch sử là Non-Goal và xử lý cả thư mục thuộc Sprint 2. Tôi vẫn đặc tả Table cho US-07 để khỏi thiết kế lại.

### 3.1 Button
| Biến thể | Nền | Chữ | Viền | Dùng cho |
|---|---|---|---|---|
| Primary | `primary` | `on-primary` | không | Upscale, Mở thư mục ở màn hình kết quả. Mỗi màn hình tối đa một nút primary |
| Secondary | `surface-alt` | `text` | `border` 1 px | Chọn ảnh, Upscale ảnh khác, Thử lại |
| Danger | `danger` | `on-danger` | không | Hủy khi đang xử lý, xác nhận hủy |

- Kích thước: cao 40 px, bo `radius-md`, đệm ngang 16 px, chữ `type-body-strong`.
- Trạng thái: mặc định, hover (`primary-hover` cho primary, nền đậm hơn một bậc cho các loại còn lại), focus (vòng 2 px `primary`, cách nút 2 px), pressed, disabled (nền `surface-alt`, chữ `text-muted`, con trỏ không đổi).
- Nút có nhãn chữ luôn có thể đọc bởi trình đọc màn hình. Không dùng nút chỉ có biểu tượng ở MVP.
- Khi đang xử lý, nút Upscale đổi nhãn thành "Đang xử lý..." và bị khóa, để người dùng thấy lý do nút không bấm được.

### 3.2 Segmented control (chọn 2x/4x và Ảnh thật/Anime)
- Hai đến ba lựa chọn, chọn đúng một. Mục đang chọn có nền `primary`, chữ `on-primary`. Mục còn lại nền `surface-alt`, chữ `text`.
- Cao 40 px, bo `radius-sm`, rộng tối thiểu 72 px mỗi mục.
- Mũi tên trái và phải đổi lựa chọn khi focus. Mục đang chọn phải phân biệt được không chỉ bằng màu: thêm dấu tích đứng trước nhãn.
- Nhãn kèm kết quả cụ thể: `2x` hiện "2x (gấp đôi)", `4x` hiện "4x (gấp bốn)". Ảnh sau khi chọn hiển thị kích thước đầu ra dự kiến, ví dụ "220 x 220 thành 880 x 880".

### 3.3 Input (chỉ đọc ở MVP)
MVP không có ô nhập chữ do người dùng gõ. Đường dẫn ảnh và đường dẫn kết quả là ô chỉ đọc cho phép bôi chọn và sao chép.
- Nền `surface-alt`, viền `border` 1 px, bo `radius-sm`, cao 40 px, chữ `type-mono`, cắt giữa đường dẫn dài bằng dấu `...` và hiện đủ khi rê chuột.
- Trạng thái lỗi (nếu sau này có ô nhập): viền `danger` 2 px, biểu tượng cảnh báo, và dòng chữ lỗi `danger` ngay dưới ô. Nhãn luôn nằm phía trên ô, không dùng placeholder thay nhãn.

### 3.4 Card
- Nền `surface`, viền `border` 1 px, bo `radius-lg`, đệm 24 px, khoảng cách giữa các phần tử trong thẻ 12 px.
- Thẻ thông báo có thêm dải màu bên trái 4 px và biểu tượng. Biến thể: thông tin (`secondary-bg`), thành công (`success-bg`), cảnh báo (`warning-bg`), lỗi (`danger-bg`). Chữ tiêu đề dùng màu chữ của trạng thái, nội dung dùng `text`.
- Thẻ thông báo lỗi có vai trò thông báo khẩn (`role="alert"` ở web). Tkinter không có tương đương trực tiếp, nên chưa chắc trình đọc màn hình sẽ đọc tự động. Xem mục 5.

### 3.5 Modal
Chỉ một hộp thoại xác nhận hủy khi đang xử lý, và hộp thoại "Giới thiệu và log" nếu cần. Không dùng hộp thoại cho lỗi.
- `CTkToplevel`, rộng 420 px, bo `radius-lg`, nền `surface`, đệm 24 px, đặt giữa cửa sổ chính, khóa cửa sổ chính (`grab_set`).
- Bố cục: tiêu đề `type-heading`, một đoạn nội dung `type-body`, hàng nút căn phải (Secondary bên trái, Primary hoặc Danger bên phải).
- Focus ban đầu nằm ở nút an toàn (Tiếp tục xử lý), `Esc` đóng hộp thoại, `Tab` xoay vòng trong hộp thoại. Đóng xong trả focus về nút đã mở nó.
- Nội dung xác nhận hủy: "Hủy xử lý ảnh này? Ảnh gốc không bị ảnh hưởng và sẽ không có file kết quả."

### 3.6 Progress
- `CTkProgressBar`, cao 10 px, bo tròn, rãnh `surface-alt`, phần đã chạy `primary`. Cạnh thanh luôn có số phần trăm bằng chữ (`type-body-strong`), vì thanh một mình không đọc được qua trình đọc màn hình.
- Trước khi engine in phần trăm đầu tiên, dùng chế độ không xác định (indeterminate) kèm chữ "Đang khởi động engine...". Khi có sự kiện `progress` đầu tiên thì chuyển sang xác định.
- Tôi chưa biết engine có in phần trăm đều đặn cho ảnh nhỏ hay không: lần spike ảnh 220x220 chỉ ghi nhận dạng `25,00%`, không ghi số lần in. Nếu ảnh nhỏ nhảy từ 0 lên 100 thì thanh chỉ có giá trị với ảnh lớn.

### 3.7 Table (cho US-07, chưa dùng ở MVP)
- Cột: Tên file, Kích thước gốc, Kết quả (hệ số), Trạng thái. Cuộn dọc trong `CTkScrollableFrame`, tiêu đề cột cố định.
- Hàng cao 40 px, nền xen kẽ `surface` và `surface-alt`, tiêu đề `type-body-strong` trên nền `surface-alt`, viền dưới `border`.
- Ô Trạng thái luôn có biểu tượng và chữ: "Chờ", "Đang xử lý X%", "Xong", "Lỗi". Chọn hàng bằng phím mũi tên, `Enter` mở thư mục chứa file.
- `CTkScrollableFrame` dựng từng hàng thành widget riêng nên có thể chậm với hàng trăm hàng. Chưa đo. Nếu lô vượt khoảng 200 ảnh, cần xem lại, ví dụ dùng `ttk.Treeview` đã tạo kiểu theo token.

## 4. Trạng thái rỗng, đang tải và lỗi

### 4.1 Trạng thái rỗng (S0)
| Thành phần | Nội dung |
|---|---|
| Vùng ảnh | Khung nét đứt `border`, biểu tượng ảnh, tiêu đề "Chưa có ảnh nào" |
| Dòng hướng dẫn | "Chọn một ảnh PNG hoặc JPG để phóng to 2x hoặc 4x. Ảnh được xử lý ngay trên máy bạn, không tải lên đâu cả." |
| Hành động | Nút Primary "Chọn ảnh" (phím tắt `Ctrl+O`), focus ban đầu nằm ở nút này |
| Điều khiển khác | Hệ số, model và nút Upscale hiện nhưng bị khóa, kèm gợi ý "Chọn ảnh trước" |

Màn hình rỗng nói rõ việc cần làm tiếp theo và nhắc ảnh không rời máy, vì đó là lý do chính của bản local.

### 4.2 Trạng thái đang tải và đang xử lý
| Giai đoạn | Hiển thị | Ghi chú |
|---|---|---|
| Mở app, kiểm tra engine | Chữ "Đang kiểm tra engine..." trên màn hình S0, các nút khóa | Chỉ kiểm tra file tồn tại, nhanh. Nếu lâu hơn 300 ms mới hiện, để tránh nhấp nháy |
| Đọc ảnh vừa chọn | Vùng ảnh hiện "Đang đọc ảnh..." | Đọc kích thước bằng Pillow, không giải mã toàn ảnh |
| Engine khởi động | Thanh tiến độ không xác định, chữ "Đang khởi động engine..." | Chuyển sang xác định khi có sự kiện `progress` đầu tiên |
| Đang xử lý | Thanh tiến độ và "Đang xử lý ảnh... 42%", nút Hủy (Danger), các điều khiển khác khóa | Cửa sổ luôn phản hồi vì engine chạy ở tiến trình con |
| Đang xem trước ảnh lớn (US-08, stretch) | Khung giữ chỗ `surface-alt` và chữ "Đang tải bản xem trước..." | Tạo ảnh thu nhỏ ở luồng nền. Chưa đo thời gian với ảnh 4000x4000 |

Không dùng khung xương (skeleton) vì màn hình chỉ có một vùng nội dung. Mỗi trạng thái đang tải đều có chữ, không chỉ có hoạt ảnh.

### 4.3 Hoàn tất (S3)
Thẻ thành công (`success-bg`, dấu tích): "Đã lưu ảnh 880 x 880" kèm ô chỉ đọc chứa đường dẫn, thời gian xử lý, nút Primary "Mở thư mục" và nút Secondary "Upscale ảnh khác". Nếu tên file có hậu tố số vì trùng tên, hiện thêm dòng "Đã có file cùng tên, ảnh được lưu thành ..._x4_2.png".

### 4.4 Thông báo lỗi
Lỗi hiện trong thẻ lỗi (`danger-bg`, biểu tượng cảnh báo) ngay trên khu vực thao tác. Mỗi thông báo có ba phần: chuyện gì xảy ra, vì sao, và việc làm tiếp theo. Không hiện stack trace. Chi tiết kỹ thuật ghi vào `logs/app.log`, và thẻ chỉ có liên kết "Mở file log".

| Mã lỗi | Tiêu đề | Nội dung | Hành động |
|---|---|---|---|
| `IMAGE_UNREADABLE` | Không đọc được ảnh | File này không phải ảnh PNG/JPG hợp lệ hoặc đã bị hỏng. | Chọn ảnh khác |
| `ENGINE_MISSING` | Thiếu engine hoặc model | Không tìm thấy: `<đường dẫn thiếu>`. Hãy chép lại thư mục `engine\realesrgan`. | Mở thư mục dự án |
| `OUTPUT_TOO_LARGE` | Ảnh kết quả quá lớn | Ảnh sẽ có kích thước `<W x H>`, vượt giới hạn máy này xử lý an toàn. Hãy thử hệ số 2x. | Chọn 2x, Upscale lại |
| `OUT_OF_VRAM` | Không đủ bộ nhớ GPU | Card đồ họa hết bộ nhớ khi xử lý ảnh này. Hãy thử hệ số 2x hoặc đóng ứng dụng đang dùng GPU. | Thử lại, Mở log |
| `ENGINE_FAILED` | Xử lý không thành công | Engine dừng với lỗi. Ảnh gốc không bị ảnh hưởng. | Thử lại, Mở log |
| `CANCELLED` | Đã hủy | Không tạo file kết quả. | Không có, về S1 |

- `CANCELLED` dùng thẻ thông tin (`secondary-bg`), không dùng thẻ lỗi, vì hủy là việc người dùng chủ động.
- Thông báo `OUTPUT_TOO_LARGE` chưa có con số giới hạn thật, vì `max_output_pixels` chưa được đo (mục 5).
- Khi lỗi xảy ra, focus chuyển sang nút hành động đầu tiên trong thẻ lỗi để người dùng bàn phím xử lý ngay.
- Thẻ lỗi nằm yên cho đến khi người dùng thao tác tiếp. Không tự biến mất sau vài giây.

## 5. Chưa kiểm chứng và việc cần làm

| Mục | Tình trạng | Việc cần làm |
|---|---|---|
| Tương phản | Đã đo trên ảnh chụp thật (8 cặp: nút 4x đang chọn, nút Hủy, nút Chọn ảnh khi bị khóa, nhãn tiến độ, tiêu đề thành công, hai nút ở S3, nhãn đường dẫn). Thấp nhất là nút 4x đang chọn 4,88:1, cao nhất 15,26:1, đều từ 4,5:1 trở lên. Chưa đo màu hover và rãnh thanh tiến độ | Đo màu hover khi cần |
| Giao diện thật | Đã dựng và chụp S0 đến S3 ở cả hai theme (11/6/2026), xem S3 sáng và S2 tối bằng mắt, không thấy lỗi bố cục | Chưa xem bằng mắt S0, S1 ở hai theme và S2 sáng, S3 tối |
| Trình đọc màn hình | Tkinter hỗ trợ hạn chế. Tôi không đảm bảo thẻ lỗi hay thanh tiến độ được đọc tự động | Nếu bạn cần, thử với Narrator. Yêu cầu của US-02 chỉ nói "bấm được bằng bàn phím", và đặc tả đáp ứng phần này |
| Phím tắt `Ctrl+O`, thứ tự `Tab` | `Ctrl+O`, Enter, Space, mũi tên và Esc đã có test bằng phím thật. Thứ tự `Tab` chưa kiểm | Kiểm thứ tự `Tab` bằng tay |
| Chữ ở DPI 125% và 150% | Đã chụp ở 125% (cửa sổ 950x700 = 760x560 nhân 1,25), nội dung vừa khung. 150% chưa thử | Thử khi đổi cỡ chữ hệ thống |
| `max_output_pixels`, `tile` | Đã đo, `max_output_pixels = 150000000`, `tile = 0` (xem `docs/DECISIONS.md`) | Kiểm tra thông báo `OUTPUT_TOO_LARGE` nêu đúng giới hạn khi người dùng gặp |
| Tiến độ ảnh nhỏ | Chưa biết engine có in nhiều mốc phần trăm cho ảnh nhỏ | Kiểm tra khi viết parser |
| Kéo thả ảnh | Không làm ở MVP, cần thư viện ngoài | Ghi vào backlog |
| Tên app, logo, biểu tượng | Chưa thiết kế, bản mẫu dùng chữ "UpScale" | Quyết định sau Sprint 1 nếu cần |

**Theo dõi rủi ro của Sprint 1:** `SPRINT-1.md` đã ghi rủi ro "giao diện đẹp hiện đại làm US-02 vượt 5 điểm". Đặc tả này có 7 component và 4 trạng thái, nên cần giữ đúng phạm vi: dựng luồng chạy được với giao diện cơ bản trước, rồi áp token. Table, hộp thoại giới thiệu và chuyển theme "Theo hệ thống" là những phần cắt đầu tiên nếu trễ.

