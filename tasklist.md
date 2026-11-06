# UpScale - Tasklist

**Cập nhật**: lần đầu, tạo từ rà soát thư mục. Nguồn: `docs/PRD.md`, `docs/SPRINT-1.md`, `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, mã trong `src/` và `tests/`.
**Quy ước**: `[x]` đã xác minh bằng lệnh/test, `[~]` có mã nhưng chưa nghiệm thu, `[ ]` chưa làm.
**Quy tắc agent**: xem `.clinerules`. Trước mỗi task, đọc file agent ghi ở cột "Agent" (đường dẫn tính từ `.agency-agents/`). Không sửa file trong `.agency-agents/`.

## Sprint Goal (Sprint 1)
Chạy app, chọn ảnh, Upscale 2x/4x khi ngắt mạng, nhận ảnh lưu cạnh file gốc. Tiêu chí: bộ 5 ảnh test (có 1 ảnh lớn) chạy 5/5, không crash, không mạng.

## Hiện trạng đã xác minh
- [x] `.venv/Scripts/python.exe -W error::ResourceWarning -m unittest discover -s tests -t .` (Python 3.11.9): 65 test đạt.
- [x] `python -m compileall src tests run.py` không lỗi.
- [x] `ruff check src tests run.py` (ruff 0.17.4): All checks passed.
- [x] Không có TODO/FIXME/placeholder trong `src/`; không import thư viện mạng (`socket`, `urllib`, `requests`, `http`) trong `src/`.
- [x] Git: đã `git init`, nhánh `main` theo dõi `origin/main` (https://github.com/nhieudo71/UpScale.git). Chưa commit hay push.
- Chưa xác minh: chạy GUI thật, offline thật, bộ 5 ảnh, build `.exe`, CI trên GitHub.

## Vấn đề phát hiện (cần xử lý)
| # | Vấn đề | Bằng chứng | Hành động |
|---|--------|------------|-----------|
| P1 | ~~`.venv` dùng Python 3.14.6, chưa cài thư viện~~ **Đã xử lý (T-01)**: tạo lại bằng Python 3.11.9, cài `requirements-dev.txt` | Test, ruff, compileall đều đạt | - |
| P2 | `README.md` ở remote chỉ có 2 dòng mô tả, chưa có hướng dẫn cài và chạy như Definition of Done yêu cầu | `git show origin/main:README.md` | Task T-08 (viết lại, giữ dòng mô tả hiện có) |
| P3 | ~~Thư mục chưa phải git repo~~ **Đã xử lý**: `git init`, gắn `origin`, `main` theo dõi `origin/main`. Còn lại: chưa commit, CI chưa chạy lần nào | `git status -sb` | Chờ người dùng cho phép commit và push (xem T-10) |
| P4 | `logs/app.log` chỉ có 1 job hoàn tất (smoke, 880x880) mất 318.640 ms, trong khi D-01 đo 5 s cho ảnh tương tự | Log 10:18 đến 10:23 | Điều tra: đo lại, kiểm tra có chạy nhầm GPU 0 (Intel) hay app đang mở song song |
| P5 | Job lúc 15:34 (ảnh trong Downloads) có dòng "Chạy engine" nhưng không có dòng "xong" hay "lỗi" | Cuối `logs/app.log` | Xác nhận do đóng app/hủy hay do treo; nếu đóng app mà không ghi log thì sửa |
| P6 | Ngày trong docs ghi `11/06/2026`, ngày file và log là 06/11/2026 | Timestamp file | Thống nhất định dạng ngày |

## Sprint 1 - Cam kết (13 điểm)

| ID | Story | Điểm | Trạng thái | Agent |
|----|-------|------|-----------|-------|
| US-01 | Engine chạy được | 3 | [~] Spike xong (D-01). Còn: kiểm tra giấy phép file model | `engineering/engineering-senior-developer.md` |
| US-02 | Upscale qua giao diện | 5 | [~] Có mã `ui/`, 65 test. Chưa nghiệm thu thủ công | `engineering/engineering-desktop-app-engineer.md`, `design/design-ui-designer.md` |
| US-04 | Ảnh lớn | 2 | [~] Đã đo tới 192 MP, `max_output_pixels=150000000`. Chưa thử ảnh chụp thật | `testing/testing-performance-benchmarker.md` |
| US-05 | Lỗi dễ hiểu | 2 | [~] Có mã lỗi và test các nhánh. Chưa thử tay trên GUI | `engineering/engineering-code-reviewer.md` |
| US-03 | Offline | 1 | [~] Mã không gọi mạng. Chưa thử ngắt mạng thật | `testing/testing-reality-checker.md` |

### Task còn lại để đóng Sprint 1
- [x] **T-01 Sửa môi trường (P1)**: venv Python 3.11.9, cài `requirements-dev.txt`, `ruff check` sạch, 65 test đạt.
  - Agent: `engineering/engineering-developer-tooling-engineer.md`
- [ ] **T-10 Commit đầu tiên và push (P3)**: chọn file đưa vào repo, tạo nhánh mới, mở PR để CI chạy.
  - Cần người dùng quyết: có đưa `.agency-agents/` (5,7 MB) vào repo không; `.gitignore` đã loại `engine/`, `config.toml`, `.env`, `logs/`, `.venv/`.
  - Agent: `engineering/engineering-git-workflow-master.md`
- [ ] **T-02 Điều tra P4, P5**: chạy lại một job 4x ảnh 220x220 qua app, so với 5 s của D-01; xem log job 15:34.
  - Xong khi: nguyên nhân được ghi vào `docs/DECISIONS.md`.
  - Agent: `engineering/engineering-minimal-change-engineer.md` nếu cần sửa mã.
- [ ] **T-03 Nghiệm thu giao diện** theo checklist demo bên dưới (chạy `python run.py`).
  - Agent: `testing/testing-evidence-collector.md`
- [ ] **T-04 Bộ ảnh test 5 ảnh** (gồm 1 ảnh lớn, nên có ảnh chụp thật), chạy 5/5 và ghi thời gian vào `docs/DECISIONS.md`.
  - Agent: `testing/testing-test-automation-engineer.md`
- [ ] **T-05 Thử offline thật** (US-03): tắt Wi-Fi, chạy bộ ảnh.
- [ ] **T-06 Giấy phép model** (câu hỏi mở cuối của PRD): kiểm tra giấy phép riêng của file model Real-ESRGAN, ghi vào D-01.
- [ ] **T-07 Chất lượng bằng mắt**: so `realesrgan-x4plus -s 2` với model anime, chọn model 2x mặc định.
- [ ] **T-08 Viết `README.md`**: cài, chạy, chép `engine/realesrgan`, cấu hình `config.toml`.
  - Agent: `engineering/engineering-technical-writer.md`
- [ ] **T-09 Kiểm tra trước bàn giao**: chạy toàn bộ test, rà TODO, đối chiếu Acceptance Criteria của US-01 đến US-05.
  - Agent: `testing/testing-reality-checker.md`

### Checklist demo cuối sprint
- [ ] Mở app, chọn ảnh, thấy kích thước gốc.
- [ ] Upscale 2x và 4x, kích thước ảnh kết quả đúng.
- [ ] Giao diện không đơ khi đang xử lý.
- [ ] Ngắt mạng, vẫn upscale được.
- [ ] Ảnh lớn không làm crash.
- [ ] Chọn file không phải ảnh, thấy thông báo lỗi dễ hiểu.
- [ ] File gốc không bị đổi, file đích không bị ghi đè.

## Stretch (chỉ làm khi cam kết xong)
- [~] **US-06 Chọn model Ảnh thật / Anime** (2 điểm): `domain/models.py` có hai model, UI có thứ tự Tab cho chọn model. Cần xác nhận log ghi đúng model.
- [ ] **US-08 Xem trước và sau** (3 điểm): chưa thấy mã.
  - Agent: `design/design-ux-architect.md`

## Sprint 2 (dự kiến)
- [ ] **US-07 Xử lý cả thư mục** (5 điểm): thêm `start_batch` theo `docs/ARCHITECTURE.md` mục 3.3.
  - Agent: `engineering/engineering-backend-architect.md`
- [ ] **Đóng gói**: `UpScale.spec`, `scripts/smoke_exe.ps1` và `.github/workflows/ci.yml` đã có; chưa build thử. Cần git repo (P3) để CI chạy.
  - Agent: `engineering/engineering-devops-automator.md`

## Backlog (chờ người dùng quyết)
- SQLite lịch sử xử lý: đang là Non-Goal, cần đổi PRD trước.
- REST API cục bộ: chỉ có thiết kế (`ARCHITECTURE.md` 3.4).
- Định dạng ảnh ngoài PNG/JPG (WebP, BMP).
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
