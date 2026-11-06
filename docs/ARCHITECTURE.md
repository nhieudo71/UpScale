# Kiến trúc kỹ thuật - UpScale

**Cập nhật**: 11/06/2026  **Vai trò**: Backend Architect + Database Optimizer (agency)
**Căn cứ**: `docs/PRD.md`, `docs/DECISIONS.md` (D-01 đến D-03)

## 0. Nguyên tắc và một điều chỉnh so với yêu cầu

Yêu cầu thiết kế có Database, Cache và REST API. PRD của dự án nói khác: một người dùng, chạy offline, không tài khoản, không cloud, và "lịch sử xử lý" nằm trong Non-Goals. Vì vậy:

- **Sprint 1 không cần database, cache hay server HTTP.** Thêm chúng là thêm tiến trình, cổng mạng và cấu hình mà không có người dùng nào hưởng lợi.
- **Ranh giới "API" là một lớp service trong tiến trình** (mục 3). Giao diện gọi service, service gọi engine. Đây là hợp đồng thật của MVP.
- **Schema SQLite (mục 2) và ánh xạ REST (mục 3.4) được thiết kế sẵn nhưng chưa xây.** Chỉ xây khi có nhu cầu thật (xử lý cả thư mục ở Sprint 2, hoặc muốn gọi từ công cụ khác).

Mô hình triển khai: **modular monolith một tiến trình**, engine chạy ở tiến trình con.

## 1. Tech Stack

| Lớp | Lựa chọn | Trạng thái | Lý do |
|---|---|---|---|
| Ngôn ngữ | Python 3.11.9 | Đã xác nhận trên máy (có pip, Tkinter 8.6) | Có sẵn, dễ gọi tiến trình con, đủ cho điều phối. Việc nặng nằm ở engine, không ở Python |
| Giao diện | CustomTkinter + Pillow | Chưa cài, kiểm tra ở US-02 | Đẹp hiện đại theo yêu cầu, không cần dựng web hay Qt |
| Engine AI | Real-ESRGAN ncnn Vulkan qua `subprocess` | Đã chạy thử trên RTX 3050 | Không cần PyTorch hay CUDA. Tiến trình con cách ly lỗi hết VRAM khỏi app |
| Cấu hình | `config.toml` đọc bằng `tomllib` | Stdlib của Python 3.11 | Không thêm thư viện |
| Log | `logging` + `RotatingFileHandler` vào `logs/app.log` | Stdlib | Đáp ứng US-05 |
| Test | `unittest` | Stdlib | Không cần cài. Có thể đổi sang pytest sau |
| Database | Không dùng ở Sprint 1. Nếu cần: SQLite qua `sqlite3` | SQLite 3.45.1 đã xác nhận | Một file, không server, không cấu hình |
| Cache | Không dùng | - | Xem bên dưới |

**Vì sao không có cache:** mỗi ảnh được xử lý một lần và kết quả là một file trên đĩa, nên không có truy vấn đọc lặp để cache. Redis cần thêm một server chạy nền, trái với mục tiêu ít phụ thuộc và offline. Nếu sau này muốn tránh xử lý lại ảnh cũ, dùng băm nội dung ảnh cộng scale cộng model làm khóa và kiểm tra file đầu ra có sẵn, không cần Redis.

**Vì sao không FastAPI, Postgres, Redis:** một người dùng, một máy. Mỗi thành phần thêm một tiến trình cần khởi động, cổng mạng cần bảo vệ và cấu hình cần giữ. Không thành phần nào giải quyết vấn đề của Sprint 1.

## 2. Thiết kế cơ sở dữ liệu (SQLite, tùy chọn từ Sprint 2)

**Khi nào xây:** chỉ khi bạn muốn bền vững hàng đợi hoặc lịch sử qua các lần mở app. Xử lý cả thư mục (US-07) chạy được bằng danh sách trong bộ nhớ, nên chưa bắt buộc. Lịch sử là Non-Goal nên cần bạn đổi PRD trước khi làm.

### Pragma khi mở kết nối
```sql
PRAGMA foreign_keys = ON;      -- SQLite tắt khóa ngoại theo mặc định
PRAGMA journal_mode = WAL;     -- đọc không chặn ghi
PRAGMA busy_timeout = 5000;
```

### Bảng
```sql
CREATE TABLE batches (
  id          INTEGER PRIMARY KEY,
  folder_path TEXT    NOT NULL,
  scale       INTEGER NOT NULL CHECK (scale IN (2,4)),
  model       TEXT    NOT NULL,
  created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE jobs (
  id            INTEGER PRIMARY KEY,
  batch_id      INTEGER REFERENCES batches(id) ON DELETE CASCADE,  -- NULL = ảnh đơn
  source_path   TEXT    NOT NULL,
  output_path   TEXT,
  scale         INTEGER NOT NULL CHECK (scale IN (2,4)),
  model         TEXT    NOT NULL,
  gpu_id        INTEGER,
  status        TEXT    NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','done','failed','cancelled')),
  error_code    TEXT,
  error_message TEXT,
  input_w INTEGER, input_h INTEGER, output_w INTEGER, output_h INTEGER,
  duration_ms   INTEGER,
  created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  finished_at   TEXT
);
```

| Trường | Ghi chú |
|---|---|
| `id` | `INTEGER PRIMARY KEY` là bí danh của rowid trong SQLite, nhanh nhất. Không cần UUID vì không có đồng bộ nhiều nơi |
| `batch_id` | Khóa ngoại tới `batches.id`. Cho phép NULL vì ảnh đơn không thuộc lô |
| `scale` | `CHECK` chỉ nhận 2 hoặc 4, khớp phạm vi MVP |
| thời gian | Lưu chuỗi ISO 8601 UTC, vì SQLite không có kiểu datetime riêng |
| đường dẫn | Lưu nguyên văn. Không dùng đường dẫn làm khóa duy nhất vì cùng một ảnh có thể xử lý nhiều lần |

### Chỉ mục
```sql
CREATE INDEX idx_jobs_batch_status ON jobs(batch_id, status);              -- tiến độ i/N và khóa ngoại
CREATE INDEX idx_jobs_queue ON jobs(created_at, id) WHERE status = 'queued'; -- lấy job kế tiếp
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);                    -- danh sách gần đây
```

| Chỉ mục | Truy vấn nó phục vụ |
|---|---|
| `idx_jobs_batch_status` | Đếm job theo trạng thái trong một lô, và xóa lô theo `ON DELETE CASCADE` (khóa ngoại phải có chỉ mục) |
| `idx_jobs_queue` | Chỉ mục một phần chỉ chứa job đang chờ, nên nhỏ dù bảng lớn dần |
| `idx_jobs_created` | Danh sách job mới nhất |

### Đã kiểm chứng
Tôi chạy schema trên SQLite 3.45.1 trong bộ nhớ và dùng `EXPLAIN QUERY PLAN`:
- Đếm theo trạng thái trong lô: dùng `idx_jobs_batch_status` dạng covering index.
- Lấy job chờ kế tiếp: dùng `idx_jobs_queue`.
- Danh sách gần đây: dùng `idx_jobs_created`.
- Tìm job theo lô khi xóa: dùng `idx_jobs_batch_status`.
- `CHECK` từ chối `scale = 3`, khóa ngoại từ chối `batch_id` không tồn tại.

**Giới hạn của phép kiểm tra:** các bảng trống và chưa có dữ liệu thật. Kế hoạch truy vấn có thể đổi khi có dữ liệu và thống kê. Với một người dùng, số dòng rất nhỏ nên hiệu năng không phải rủi ro. Tôi chưa đo thời gian truy vấn.

### Migration
Dùng `PRAGMA user_version` làm số phiên bản schema. Mỗi migration là một file `migrations/NNN_ten.sql` và có file đảo ngược `NNN_ten.down.sql`. Lưu ý: nếu `ALTER TABLE` kiểu phức tạp, SQLite phải tạo bảng mới rồi sao chép dữ liệu.

## 3. Hợp đồng API

### 3.1 Ranh giới thật của MVP: service trong tiến trình
Giao diện không gọi engine trực tiếp. Nó gọi `UpscaleService`, và service này là nơi duy nhất biết về `subprocess`. Giao diện cập nhật bằng sự kiện đẩy qua `queue.Queue`, vì Tkinter chỉ an toàn khi cập nhật widget từ luồng chính.

```python
class UpscaleService:
    def inspect_image(self, path: str) -> ImageInfo: ...
    def start(self, req: UpscaleRequest, on_event: Callable[[JobEvent], None]) -> str: ...  # trả job_id
    def cancel(self, job_id: str) -> None: ...
    def list_models(self) -> list[ModelInfo]: ...
    def list_gpus(self) -> list[GpuInfo]: ...
```

**UpscaleRequest**
| Trường | Kiểu | Quy tắc |
|---|---|---|
| `source_path` | str | Tồn tại, đọc được bằng Pillow, đuôi PNG/JPG |
| `scale` | int | 2 hoặc 4 |
| `model` | str | `photo` (mặc định, `realesrgan-x4plus`) hoặc `anime` (`realesrgan-x4plus-anime`) |
| `gpu_id` | int hoặc null | Null = dùng `gpu_id` trong `config.toml` |

**JobEvent** (đẩy theo thứ tự `started`, nhiều `progress`, rồi đúng một `done` hoặc `failed`)
```json
{"job_id": "a1b2", "type": "progress", "percent": 25.0}
{"job_id": "a1b2", "type": "done", "output_path": "D:\\Anh\\cat_x4.png", "output_w": 880, "output_h": 880, "duration_ms": 5070}
{"job_id": "a1b2", "type": "failed", "code": "OUT_OF_VRAM", "message": "Không đủ bộ nhớ GPU. Thử hệ số 2x.", "log_ref": "logs/app.log"}
```

**Mã lỗi** (khớp US-05, thông báo tiếng Việt cho người dùng, chi tiết kỹ thuật chỉ vào log)
| Mã | Khi nào |
|---|---|
| `IMAGE_UNREADABLE` | File không phải ảnh hoặc bị hỏng |
| `ENGINE_MISSING` | Thiếu `.exe` hoặc thư mục model, thông báo nêu đường dẫn thiếu |
| `OUTPUT_TOO_LARGE` | Kích thước đầu ra vượt `max_output_pixels`, chặn trước khi chạy |
| `OUT_OF_VRAM` | Engine thoát với mã khác 0 và log nêu lỗi bộ nhớ |
| `ENGINE_FAILED` | Engine thoát với mã khác 0, lý do khác |
| `CANCELLED` | Người dùng hủy |

**Quy tắc cài đặt, rút từ spike (D-01)**
- Thành công khi `returncode == 0` và file đầu ra tồn tại. Không dùng nội dung stderr để kết luận lỗi.
- Đọc stderr theo dòng để lấy tiến độ. Regex chấp nhận cả `25,00%` và `25.00%`.
- Gọi engine bằng danh sách đối số, không dùng `shell=True`: `[exe, "-i", src, "-o", dst, "-n", model, "-s", scale, "-g", gpu_id]`. Đường dẫn do người dùng chọn nên không được ghép vào chuỗi lệnh.
- Ghi vào file tạm cạnh đích, kiểm tra kích thước đầu ra bằng `scale x` kích thước gốc, rồi mới đổi tên thành `<tên>_x<scale>.png`. Nếu đích có sẵn thì thêm hậu tố số. File gốc chỉ được mở để đọc.
- Đặt timeout cho tiến trình con (cấu hình được) và kết thúc tiến trình khi hủy hoặc đóng app.
- Một job chạy tại một thời điểm, vì GPU 4 GB không nên chạy song song.
- Không có lời gọi mạng nào trong mã (US-03).

**`config.toml`**
```toml
gpu_id = 1                   # chọn GPU NVIDIA, không cố định theo chỉ số
tile = 0                     # 0 = tự động. Đã đo tới 192 MP đầu ra, VRAM đỉnh khoảng 1,3 GB nên không cần đặt số
max_output_pixels = 150000000 # 150 MP. Giới hạn do Pillow (không mở được trên 179 MP), không do GPU
engine_timeout_s = 600
```
Hai giá trị `tile` và `max_output_pixels` đã đo ngày 11/6/2026, kết quả và hạn chế nằm ở `docs/DECISIONS.md` mục "Đo ảnh lớn bằng engine thật".

### 3.2 Hàm service theo story
| Hàm | Dùng ở story |
|---|---|
| `inspect_image` | US-02 (tên và kích thước gốc), US-05 |
| `start`, `cancel` | US-02, US-04 |
| `list_models` | US-06 |
| `list_gpus` | Cấu hình `gpu_id` (D-01 mục 1) |

### 3.3 Hàng loạt (US-07, Sprint 2)
Thêm `start_batch(folder, scale, model, on_event)`. Sự kiện thêm `batch_progress {done, failed, total}`. Một ảnh lỗi không dừng lô. Cuối lô trả `batch_done {succeeded, failed}`.

### 3.4 REST (chỉ thiết kế, không xây ở MVP)
Chỉ thêm nếu bạn muốn gọi từ công cụ khác. Khi đó, mỗi route bọc đúng một hàm service ở trên, và **chỉ bind `127.0.0.1`**. Không đặt `0.0.0.0` vì API nhận đường dẫn file tùy ý và sẽ đọc ghi trên máy bạn. Chưa có xác thực, nên trước khi xây cần kiểm tra `source_path` nằm trong thư mục cho phép.

| Phương thức | Đường dẫn | Body | Phản hồi |
|---|---|---|---|
| POST | `/v1/images/inspect` | `{"path": "..."}` | 200 `{width, height, format}`, 422 `IMAGE_UNREADABLE` |
| POST | `/v1/jobs` | `UpscaleRequest` | 202 `{job_id, status: "queued"}`, 422 `OUTPUT_TOO_LARGE` |
| GET | `/v1/jobs/{id}` | - | 200 `{status, percent, output_path?, error?}`, 404 |
| GET | `/v1/jobs/{id}/events` | - | Luồng SSE các `JobEvent` |
| DELETE | `/v1/jobs/{id}` | - | 204, hủy job |
| GET | `/v1/models` | - | 200 `[{id, label, scales}]` |
| GET | `/v1/gpus` | - | 200 `[{id, name}]` |
| POST | `/v1/batches` | `{folder, scale, model}` | 202 `{batch_id, total}` |

Lỗi dùng chung dạng `{"error": {"code": "...", "message": "..."}}`.

## 4. Cấu trúc thư mục

Kiến trúc module hóa, phụ thuộc một chiều: `ui` gọi `services`, `services` gọi `domain` và `infra`. `domain` không import gì từ các lớp khác. Cấu trúc này nhẹ hơn Clean Architecture đầy đủ vì MVP chỉ có một use case chính.

```
D:\APP\UpScale\
├─ .clinerules
├─ .agency-agents\                  # không sửa
├─ config.toml
├─ requirements.txt                 # pin phiên bản customtkinter, Pillow
├─ run.py                           # điểm vào: python run.py
├─ docs\                            # PRD, SPRINT-1, DECISIONS, ARCHITECTURE
├─ engine\realesrgan\               # exe + models (đã có, ~50 MB)
├─ logs\                            # app.log (xoay vòng)
├─ migrations\                      # chỉ khi dùng SQLite (Sprint 2+)
├─ src\upscale\
│  ├─ domain\                       # dữ liệu và quy tắc thuần, không I/O
│  │  ├─ models.py                  # UpscaleRequest, JobEvent, ImageInfo, ErrorCode
│  │  └─ rules.py                   # kiểm tra scale, kích thước đầu ra, đặt tên file
│  ├─ services\
│  │  └─ upscale_service.py         # điều phối, một job tại một thời điểm, phát sự kiện
│  ├─ infra\
│  │  ├─ engine_runner.py           # subprocess, parse stderr, timeout, hủy
│  │  ├─ image_io.py                # Pillow: đọc kích thước, kiểm tra ảnh
│  │  ├─ config.py                  # đọc config.toml bằng tomllib
│  │  ├─ logging_setup.py
│  │  └─ repository.py              # SQLite, thêm ở Sprint 2 nếu cần
│  └─ ui\
│     ├─ app.py                     # cửa sổ CustomTkinter, theme
│     ├─ views.py                   # chọn ảnh, tùy chọn, tiến độ, kết quả
│     └─ event_bridge.py            # queue.Queue và after() đưa sự kiện về luồng chính
└─ tests\
   ├─ test_rules.py
   ├─ test_engine_runner.py         # engine giả in `25,00%` và thoát mã khác 0
   └─ test_upscale_service.py
```

**Lý do tách như vậy**
- `engine_runner.py` là chỗ duy nhất đổi nếu thay engine. Phần còn lại không đổi.
- `domain/rules.py` thuần nên test được mà không cần GPU hay giao diện.
- `event_bridge.py` giữ ràng buộc luồng của Tkinter ở một chỗ.
- Test dùng engine giả để chạy nhanh và kiểm tra được nhánh lỗi mà không cần làm hết VRAM thật.

## 5. Việc còn mở
| Mục | Cần để |
|---|---|
| Đo ảnh lớn hơn 1 megapixel, tìm `tile` an toàn | Điền `max_output_pixels` và `tile` (US-04) |
| Xem chất lượng bằng mắt, so `realesrgan-x4plus -s 2` với model anime | Chọn model 2x mặc định |
| Cài `customtkinter`, `Pillow` | Bắt đầu US-02 |
| Bạn xác nhận có muốn lịch sử xử lý | Quyết định có xây SQLite và đổi Non-Goals của PRD |
| Bạn xác nhận có cần REST | Quyết định có xây mục 3.4 |
