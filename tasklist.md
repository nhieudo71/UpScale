# UpScale - Tasklist

**Cập nhật**: 06/11/2026, sau phiên rà soát và kiểm tra bằng engine thật. Nguồn: `docs/PRD.md`, `docs/SPRINT-1.md`, `docs/DECISIONS.md` (D-04, D-05 và mục "Nghiệm thu Sprint 1"), mã trong `src/` và `tests/`.
**Quy ước**: `[x]` đã xác minh bằng lệnh/test, `[~]` làm một phần hoặc chỉ có bằng chứng gián tiếp, `[ ]` chưa làm.
**Quy tắc agent**: xem `.clinerules`. Trước mỗi task, đọc file agent ghi ở cột "Agent" (đường dẫn tính từ `.agency-agents/`). Không sửa file trong `.agency-agents/`.

## Sprint Goal (Sprint 1)
Chạy app, chọn ảnh, Upscale 2x/4x khi ngắt mạng, nhận ảnh lưu cạnh file gốc. Tiêu chí: bộ 5 ảnh test (có 1 ảnh lớn) chạy 5/5, không crash, không mạng.

## Hiện trạng đã xác minh
- [x] 68 test đạt: `.venv/Scripts/python.exe -W error::ResourceWarning -m unittest discover -s tests -t .` (Python 3.11.9).
- [x] `ruff check src tests run.py` (ruff 0.17.4): All checks passed. `compileall` không lỗi.
- [x] Engine thật + `UpscaleService`, 5 ảnh (có 1 ảnh 3000x2000): 5/5 đúng kích thước, file gốc không đổi, không ghi đè. Chi tiết ở `docs/DECISIONS.md`.
- [x] Không có kết nối mạng thấy được lúc chạy (socket Python bị chặn, 0 lần thử; lấy mẫu TCP/UDP của tiến trình engine, 0 kết nối). Đây chưa phải thử ngắt mạng thật.
- [x] `python run.py` sống sau 8 giây. `pyinstaller UpScale.spec` build được và `scripts/smoke_exe.ps1` đạt. Đã xóa `build/` và `dist/` sau khi thử.
- [x] Git: nhánh `chore/initial-import` đã push lên origin. `main` chưa bị đụng.
- Chưa xác minh: thao tác GUI bằng tay, ngắt Wi-Fi thật, ảnh chụp thật nhiều chi tiết, CI trên GitHub (chưa có PR).

## Vấn đề phát hiện
| # | Vấn đề | Trạng thái |
|---|--------|-----------|
| P1 | `.venv` dùng Python 3.14.6 | **Đã xử lý (T-01)**: tạo lại bằng 3.11.9 |
| P2 | README chỉ có 2 dòng | **Đã xử lý (T-08)**: viết lại, giữ dòng mô tả gốc |
| P3 | Chưa là git repo | **Đã xử lý**: `git init`, commit, push nhánh `chore/initial-import` |
| P4 | Job smoke 06/11 10:18 mất 318,6 s | **Chưa giải thích được**: cùng ảnh nay chạy 2,5 s qua service, hai lần liên tiếp. Nghi tranh chấp GPU lúc đó, chưa xác nhận. Xem `docs/DECISIONS.md` |
| P5 | Job 15:34 (Downloads) không có dòng "xong"/"lỗi", file tạm `.01a19a93-...tmp.png` còn lại | **Chưa giải thích hết**: engine đã chạy xong (file tạm đọc được 6688x3764) rồi app dừng trước khi đổi tên. Tôi không xóa file này. Cần bạn xem lại hôm đó có đóng app giữa chừng không |
| P6 | Docs ghi ngày `11/06/2026`, file và log là 06/11/2026 | Chưa đổi, cần bạn cho biết định dạng ngày muốn dùng (docs có thể đang theo dd/mm hoặc mm/dd) |
| P7 | **Engine crash khi đường dẫn đầu ra có Unicode** (vd `_ĐẢNG`), log 17:39 | **Đã sửa (D-04)**, có test và đã thử lại bằng engine thật |
| P8 | **`-s 2` cho ảnh sai nội dung** (tile bị lặp), dù đúng kích thước | **Đã sửa (D-05)**: 2x = chạy 4x rồi thu nhỏ. Có test; đã thử bằng engine thật |
| P9 | Khi app bị tắt giữa job, file tạm `.<tên>_x4.<job>.tmp.png` mồ côi (có thể hàng chục MB) | Chưa sửa, ghi vào Backlog |

## Sprint 1 - Cam kết (13 điểm)

| ID | Story | Điểm | Trạng thái | Agent |
|----|-------|------|-----------|-------|
| US-01 | Engine chạy được | 3 | [x] Chạy thật trên RTX 3050. Giấy phép: MIT (ncnn-vulkan) và BSD 3-Clause (Real-ESRGAN) đã đối chiếu; giấy phép riêng của file model chưa xác nhận | `engineering/engineering-senior-developer.md` |
| US-02 | Upscale qua giao diện | 5 | [~] Luồng service chạy đúng bằng engine thật, 68 test (gồm test cửa sổ Tk). Chưa ai thao tác GUI bằng tay | `engineering/engineering-desktop-app-engineer.md`, `design/design-ui-designer.md` |
| US-04 | Ảnh lớn | 2 | [~] Ảnh 3000x2000 chạy 2x và 4x được (~66 s). Chưa thử ảnh chụp thật | `testing/testing-performance-benchmarker.md` |
| US-05 | Lỗi dễ hiểu | 2 | [~] Có mã lỗi và test từng nhánh. Chưa thử tay trên GUI | `engineering/engineering-code-reviewer.md` |
| US-03 | Offline | 1 | [~] Bằng chứng gián tiếp (0 kết nối). Chưa tắt Wi-Fi thật | `testing/testing-reality-checker.md` |

### Task
- [x] **T-01 Môi trường**: venv 3.11.9, thư viện, ruff sạch.
- [x] **T-10 Commit đầu và push**: commit `Import UpScale Sprint 1 codebase` lên nhánh `chore/initial-import`, tác giả `nhieudo71 <nhieudo71@gmail.com>`. Máy chưa cài `gh` nên chưa mở PR. Mở bằng link: https://github.com/nhieudo71/UpScale/pull/new/chore/initial-import
- [x] **T-02 Điều tra log**: tìm ra P7, P8. P4 và P5 chỉ giải thích được một phần (xem bảng trên).
- [~] **T-04 Bộ 5 ảnh**: chạy 5/5 bằng engine thật, nhưng 4 trong 5 ảnh là ảnh mẫu của engine hoặc ảnh tổng hợp, và 2x của 4 ảnh đó chưa đo lại sau D-05. Còn cần ảnh chụp thật của bạn.
  - **Cập nhật (06/11)**: chạy thêm ảnh chụp thật (ầm mẫu công khai của rembg: người 600x399, hổ 1000x667, ô tô 480x360), mỗi ảnh 2x + 4x + xóa nền = 9 lượt, đều đúng kích thước, file gốc không đổi. Thời gian 2x: 4,5 đến 9,6 s; 4x: 3,9 đến 9,1 s. Vẫn còn: ảnh chụp của chính bạn.
- [ ] **T-05 Offline** (cần bạn): tắt Wi-Fi thật rồi chạy. Máy không ai dùng nên tôi không tự tắt mạng. Bằng chứng hiện có: socket Python bị chặn 0 lần gọi, engine không có kết nối TCP/UDP, toàn bộ mã không import thư viện mạng.
- [~] **T-06 Giấy phép model**: license mã nguồn đã đối chiếu. File model chưa có license riêng được xác nhận (README của engine không nói). Áp dụng thêm cho `u2net.onnx` (D-06).
- [x] **T-07 Chất lượng bằng mắt**: so 3 model xóa nền và 2 model upscale trên ảnh thật. Chọn `u2net` cho xóa nền (D-06). Model ảnh thật vẫn là mặc định cho upscale.
- [x] **T-08 README.md**: cài, chạy, cấu hình, phát triển, giấy phép, mục Xóa nền.
- [~] **T-03 Nghiệm thu GUI**: đã tự động hóa (cửa sổ thật, engine thật, model thật, gọi đúng hàm nút bấm): **15/15 mục đạt**, gồm 2x, 4x, không ghi đè, ảnh lớn không đơ (vòng lặp Tk chậm nhất 110 ms), hủy giữa chừng về S1 trong 0,2 s không còn file tạm, file không phải ảnh, xóa nền, ẩn tùy chọn khi xóa nền, đóng app. Còn thiếu: đánh giá cảm quan bằng mắt và thao tác chuột thật.
  - Agent: `testing/testing-evidence-collector.md`
- [ ] **T-09 Kiểm tra trước bàn giao**: chờ T-05 và phần cảm quan của T-03.
  - Agent: `testing/testing-reality-checker.md`

### Checklist demo cuối sprint (kiểm tra tự động 06/11, còn lại cần bạn)
- [x] Mở app, chọn ảnh, thấy kích thước gốc.
- [x] Upscale 2x và 4x, kích thước ảnh kết quả đúng.
- [x] Giao diện không đơ khi đang xử lý.
- [ ] Tắt Wi-Fi, vẫn upscale được.
- [x] Ảnh lớn không làm crash.
- [x] Chọn file không phải ảnh, thấy thông báo lỗi dễ hiểu.
- [x] File gốc không bị đổi, file đích không bị ghi đè.
- [x] Ảnh trong thư mục có dấu (vd `_ĐẢNG`) chạy được (engine thật, D-04).
- [x] Chế độ Xóa nền: ra PNG trong suốt đúng kích thước, ẩn tùy chọn phóng to.

## Stretch
- [~] **US-06 Chọn model Ảnh thật / Anime** (2 điểm): có trong `domain/models.py` và UI; hai model đã chạy được bằng engine thật ở 2x. Chưa thử tay trên GUI.
- [ ] **US-08 Xem trước và sau** (3 điểm): chưa có mã.
  - Agent: `design/design-ux-architect.md`

## Sprint 2 (dự kiến)
- [ ] **US-07 Xử lý cả thư mục** (5 điểm): `start_batch` theo `docs/ARCHITECTURE.md` mục 3.3.
  - Agent: `engineering/engineering-backend-architect.md`
- [~] **Đóng gói**: build `.exe` và smoke test đạt trên máy này. Còn thiếu: chạy CI trên GitHub (cần mở PR) và thử `.exe` với engine thật.
  - Agent: `engineering/engineering-devops-automator.md`

## Backlog (chờ bạn quyết)
- Dọn file tạm mồ côi khi khởi động app (P9). Cần quyết: dọn tự động, hay chỉ báo.
- ~~Tính năng "xóa nền"~~ **Đã có mã (D-06)**: module `src/upscale/bgremoval/`, 33 test mới, 101 test toàn bộ. Còn lại: thao tác GUI bằng tay, xác nhận giấy phép file `u2net.onnx`, cập nhật PRD (Non-Goals đang ghi "chỉnh sửa ảnh"), thử trong `.exe`, cải thiện ảnh anime và độ sắc viền.
- SQLite lịch sử xử lý: đang là Non-Goal, cần đổi PRD trước.
- REST API cục bộ: chỉ có thiết kế (`ARCHITECTURE.md` 3.4).
- Định dạng ảnh ngoài PNG/JPG (WebP, BMP).
- Thêm file LICENSE cho repo.
- Rà bảo mật mã sinh bởi AI: `security/security-ai-generated-code-auditor.md`.

## Bảng chọn agent nhanh
Đầy đủ ở `.clinerules`. Hay dùng cho dự án này:

| Việc | File agent |
|------|-----------|
| Quản lý task, cập nhật file này | `project-management/project-manager-senior.md` |
| Tính năng mới | `engineering/engineering-senior-developer.md` |
| Sửa lỗi nhỏ | `engineering/engineering-minimal-change-engineer.md` |
| Review code | `engineering/engineering-code-reviewer.md` |
| UI desktop | `engineering/engineering-desktop-app-engineer.md` |
| Test tự động | `testing/testing-test-automation-engineer.md` |
| Kiểm tra trước bàn giao | `testing/testing-reality-checker.md` |
| Điều phối nhiều agent | `specialized/agents-orchestrator.md` |

## Cách cập nhật file này
1. Làm xong task thì đổi `[ ]` thành `[x]` và ghi lệnh hoặc bằng chứng đã kiểm tra.
2. Yêu cầu mới giữa sprint ghi vào Backlog, không thêm vào cam kết.
3. Phát hiện vấn đề mới thì thêm vào bảng "Vấn đề phát hiện".
