# Tổng kết Fandom discovery — 2026-10-05

## Phạm vi và lệnh chạy

Lần chạy kiểm tra CLI bước **2.1** và thăm dò khả năng API. Chưa phải crawl đầy đủ hay hoàn tất bước 2.

Chạy từ `services/data/`:

```bash
FANDOM_USER_AGENT="LiqiDataBot/0.1 (contact: dinhan.0321@gmail.com)" \
uv run liqi-data discover
```

- API: `https://arenaofvalor.fandom.com/api.php`.
- Tốc độ cấu hình: 1 request/giây; mỗi probe thực hiện 1 attempt.
- Thời gian lần chạy cuối: `2026-10-05T06:34:59+00:00` → `2026-10-05T06:35:07+00:00` (UTC).
- Artifacts: `services/data/artifacts/discovery/<probe>.json` và `_manifest.json`.
- Mỗi record lưu HTTP status, URL/parameters, thời gian fetch, response body và thông tin chẩn đoán.

## Kết quả lần chạy cuối

| Probe | HTTP | Kết quả |
| --- | --- | --- |
| `robots_txt` | 403 | Cloudflare trả HTML challenge; chưa đọc được quy tắc robots |
| `siteinfo` | 200 | JSON API thành công |
| `allcategories_first_page` | 200 | JSON trang đầu; chưa duyệt continuation |
| `revisions_airi` | 200 | JSON revision và main-slot wikitext |
| `revisions_airi_formatversion2` | 200 | JSON với `formatversion=2` |
| `revisions_sonic_boots` | 200 | JSON revision thành công |
| `parse_sections_airi` | 200 | JSON danh sách section |
| `images_airi` | 200 | JSON tên file ảnh tham chiếu |
| `missing_page` | 200 | JSON mô tả trang không tồn tại; kết quả hợp lệ của probe |

**8/9 probe thành công; cả 8 probe API trả HTTP 200.** CLI vẫn trả exit code `1` vì `robots_txt` được phân loại `http_error`. Không diễn giải exit code này thành toàn bộ API thất bại.

## Quan sát đã xác minh

- `Airi`: page ID `4051`, revision ID `17441`, timestamp nguồn `2026-01-25T09:14:35Z`; response chứa `slots.main` và wikitext với template `HeroInformationBox2`.
- `images_airi` chứa tên file thật, gồm `File:Airi Splash Art.jpg`. Chưa gọi `imageinfo`; chưa xác minh URL ảnh, giấy phép hoặc attribution.
- Trang thiếu trả `query.pages["-1"]` với `missing: ""` trong format mặc định. HTTP 200 ở đây không có nghĩa trang tồn tại.
- HTTP 200 của probe không tự xác minh đầy đủ cấu trúc, field mapping hay tính đại diện của trang mẫu.

## Diễn biến lỗi và giới hạn kết luận

Lần đầu cả 9 probe trả HTTP 403. Response `siteinfo` có server `cloudflare` và HTML `Just a moment...`, không phải JSON. Script gọi `response.json()` vì vậy phát sinh `JSONDecodeError`.

Sau đó thử curl thành công, thử lại httpx thành công, rồi chạy lại CLI thu được kết quả trên. **Không sửa code giữa các lần thử này để làm request thành công.**

Chưa xác định nguyên nhân Cloudflare thay đổi kết quả. Không đủ bằng chứng kết luận do User-Agent, IP, TLS fingerprint hoặc thư viện HTTP. User-Agent có email thật cũng từng nhận 403 ở lần đầu.

Lần chạy cuối ghi đè các file probe cùng tên và manifest. Artifacts hiện tại phản ánh lần chạy cuối, không lưu đầy đủ lịch sử các lần thất bại trước đó.

## Blocker: robots.txt

`https://arenaofvalor.fandom.com/robots.txt` vẫn trả HTTP 403 với Cloudflare challenge. Chưa biết nội dung quy tắc robots; không coi response này là cho phép crawl hoặc là nội dung `Disallow: /`.

Hành động tiếp theo:

1. Kiểm tra robots.txt bằng trình duyệt và hướng dẫn API/điều khoản Fandom; ghi nguồn và ngày xác minh.
2. Nếu vẫn không đọc được, liên hệ Fandom để xác nhận cách truy cập tự động được hỗ trợ.
3. Tạm dừng crawl hàng loạt trong khi chưa xác minh; giữ artifacts 403 làm bằng chứng, không âm thầm bỏ qua blocker.

## Trạng thái kế hoạch

- **2.1:** chức năng gọi probe và lưu metadata/body đã chạy với dữ liệu thật.
- **2.2–2.7:** mới có bằng chứng thăm dò ban đầu; chưa hoàn tất continuation, xác minh category, bộ mẫu đủ số lượng, dependencies và media metadata.
- **2.8:** tài liệu này ghi tổng kết/blocker; chưa hoàn tất config category/template/field mapping đã xác minh.
- **2.9:** chưa hoàn tất bộ fixture và thông tin giấy phép/attribution.
- **Acceptance gate bước 2:** chưa đạt; còn thiếu extraction path và fixture cho mỗi loại entity, cùng xác minh chính sách truy cập.

Không coi response Cloudflare hoặc fixture offline là bằng chứng crawl nguồn thành công. Các response API thành công hiện tại là bằng chứng truy cập kỹ thuật tại thời điểm chạy, không phải bảo đảm truy cập lâu dài hay quyền crawl.
