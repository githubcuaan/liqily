---
categories:
  - "[[Reference Guides]]"
subjects:
  - "[[Web Development]]"
  - "[[Data Science & ML]]"
type: reference-guide
status: done
created: 2026-09-22
---
# Arena of Valor Wiki — Fandom API Endpoints

*Tất cả endpoint trên `arenaofvalor.fandom.com/api.php` để crawl dữ liệu cho LiqiWiki, chia theo hai phase: 0.1 (metadata cơ bản) và 1.0 (bổ sung + cập nhật).*

---

## Setup

```
Base URL: https://arenaofvalor.fandom.com/api.php
```

| Setting | Ghi chú |
|---------|---------|
| CORS | Thêm `&origin=*` khi gọi từ browser/JS |
| User-Agent | Bắt buộc set khi dùng script — Fandom chặn 402/403 nếu không có |
| Rate limit | **1–2 req/giây** an toàn |
| Output format | Luôn dùng `&format=json` |

**Trước khi crawl, kiểm tra wiki có extension gì:**

```
# Danh sách category thực tế
action=query&list=allcategories&aclimit=500&format=json

# Extension đang bật (Cargo, SMW...)
GET /wiki/Special:Version

# Bảng Cargo (nếu có — nguồn dữ liệu sạch nhất)
GET /wiki/Special:CargoTables
```

---

# LiqiWiki 0.1 — Metadata cơ bản

## Heroes (Tướng)

Flow: **Category list → Page detail → Infobox/Skills → Images**

### Bước 1: Liệt kê tất cả tướng

```
action=query&list=categorymembers&cmtitle=Category:Heroes&cmlimit=500&format=json
```

Response trả về danh sách page titles (tên tướng). Dùng `cmcontinue` để lấy trang tiếp nếu >500.

### Bước 2: Lấy chi tiết một tướng

**Cách A — Wikitext (chứa infobox gốc):**

```
action=query&prop=revisions&titles=Airi&rvprop=content&rvslots=main&format=json
```

Infobox dạng `{{Hero infobox| ... }}` — chứa máu, sát thương, kỹ năng, vai trò. Cần parse template ở client.

**Cách B — HTML render (dễ đọc hơn):**

```
action=parse&page=Airi&prop=wikitext|text|images&format=json
```

Trả về cả wikitext lẫn HTML đã render + danh sách ảnh.

**Cách C — Cargo query (nếu wiki có Cargo — ưu tiên nhất):**

```
action=cargoquery&tables=Heroes&fields=_pageName,Role,Damage_Type,Attack_Type&format=json
```

Dữ liệu đã chuẩn hóa thành bảng — không cần parse wikitext.

### Bước 3: Lấy ảnh tướng

```
action=query&titles=File:Airi_icon.png&prop=imageinfo&iiprop=url&format=json
```

### Dữ liệu kỳ vọng từ một tướng

| Field | Nguồn | Ghi chú |
|-------|-------|---------|
| Tên | page title | |
| Vai trò (Role) | infobox / Cargo | Warrior, Mage, Assassin... |
| Loại sát thương | infobox / Cargo | Physical, Magic |
| Chỉ số cơ bản | infobox | HP, ATK, DEF, MP... |
| Kỹ năng (skills) | infobox section | 4 skills + passive |
| Icon / ảnh | `imageinfo` | URL ảnh render |
| Skin list | section `== Skins ==` | Xem LiqiWiki 1.0 |

---

## Skills (Kỹ năng)

Kỹ năng thường nằm **trong trang tướng** dưới dạng section hoặc sub-template, không có category riêng.

### Lấy section kỹ năng của tướng

```
action=parse&page=Airi&prop=sections&format=json
```

Response trả về danh sách sections — tìm section chứa "Skills" hoặc "Abilities", lấy `index`.

```
action=parse&page=Airi&section={index}&prop=wikitext|text&format=json
```

### Dữ liệu kỳ vọng từ một skill

| Field | Ghi chú |
|-------|---------|
| Tên skill | |
| Mô tả | Damage, hiệu ứng, cooldown |
| Mana cost | |
| Skill type | Passive, Active, Ultimate |

---

## Equipment (Trang bị)

### Bước 1: Liệt kê tất cả trang bị

```
action=query&list=categorymembers&cmtitle=Category:Equipment&cmlimit=500&format=json
```

### Bước 2: Lấy chi tiết trang bị

```
action=query&prop=revisions&titles=Sonic_Boots&rvprop=content&rvslots=main&format=json
```

Hoặc Cargo:

```
action=cargoquery&tables=Equipment&fields=_pageName,Price,Stats,Passive&format=json
```

### Dữ liệu kỳ vọng

| Field | Ghi chú |
|-------|---------|
| Tên | |
| Giá | Gold |
| Stats | +ATK, +DEF, +HP... |
| Passive / Active | Hiệu ứng đặc biệt |
| Tree path | Trang bị nâng cấp từ đâu |

---

## Maps (Bản đồ)

```
action=query&list=categorymembers&cmtitle=Category:Maps&cmlimit=500&format=json
```

```
action=query&prop=revisions&titles=Antaris_Battlefield&rvprop=content&rvslots=main&format=json
```

---

## Game Modes (Chế độ chơi)

```
action=query&list=categorymembers&cmtitle=Category:Game_Modes&cmlimit=500&format=json
```

```
action=query&prop=revisions&titles=5v5&rvprop=content&rvslots=main&format=json
```

---

## Search (Tìm kiếm)

### Full-text search

```
action=query&list=search&srsearch=Airi&srlimit=20&format=json
```

### Search theo namespace

```
action=query&list=search&srsearch=Airi&srnamespace=0&format=json
```

### Autocomplete (OpenSearch)

```
action=opensearch&search=Air&limit=10&format=json
```

---

# LiqiWiki 1.0 — Bổ sung & Cập nhật

## Gems (Ngọc)

```
action=query&list=categorymembers&cmtitle=Category:Gems&cmlimit=500&format=json
```

```
action=query&prop=revisions&titles=Warrior_Gem&rvprop=content&rvslots=main&format=json
```

---

## Enchantments (Phụ trợ)

```
action=query&list=categorymembers&cmtitle=Category:Enchantments&cmlimit=500&format=json
```

```
action=query&prop=revisions&titles=Flicker&rvprop=content&rvslots=main&format=json
```

---

## Emblems (Phù hiệu)

```
action=query&list=categorymembers&cmtitle=Category:Emblems&cmlimit=500&format=json
```

```
action=query&prop=revisions&titles=Curse_of_Death&rvprop=content&rvslots=main&format=json
```

---

## Skins (Trang phục)

Skins thường **nằm trong trang tướng** chứ không có category riêng.

### Cách lấy danh sách skin của tướng

```
action=parse&page=Airi&prop=sections&format=json
```

Tìm section title chứa "Skins", lấy index:

```
action=parse&page=Airi&section={skin_section_index}&prop=wikitext|text&format=json
```

Hoặc tìm subpage:

```
action=query&prop=revisions&titles=Airi/Skins&rvprop=content&rvslots=main&format=json
```

### Dữ liệu kỳ vọng

| Field | Ghi chú |
|-------|---------|
| Tên skin | |
| Rarity | Normal, Rare, Epic, Legendary... |
| Giá | Gold / Gems / cash |
| Ảnh preview | URL từ `imageinfo` |

---

## Quy trình cập nhật dữ liệu

### Recent changes toàn wiki

```
action=query&list=recentchanges&rcprop=title|timestamp|ids|user|comment&rclimit=500&format=json
```

### Revision history một trang

```
action=query&prop=revisions&titles=Airi&rvprop=timestamp|user|comment|ids&rvlimit=50&format=json
```

Dùng để biết khi nào tướng/skill được cập nhật, lấy diff.

### RSS/Atom feed (poll định kỳ)

```
https://arenaofvalor.fandom.com/api.php?action=feedrecentchanges&feedformat=atom
```

### Admin log events

```
action=query&list=logevents&lelimit=100&format=json
```

Hữu ích khi tướng đổi tên, skill đổi URL.

### Export batch (backup/đồng bộ)

```
GET /wiki/Special:Export/Airi
```

> Export nhiều trang cùng lúc bằng POST với danh sách `pages`.

---

## Deployment Notes

- **Ưu tiên Cargo trước, wikitext-parsing sau** — Cargo đã chuẩn hóa; parse wikitext dễ vỡ khi wiki đổi infobox
- **Rate limit:** Fandom chặn gắt request không có User-Agent giống browser thật
- **Bản quyền:** Nội dung Fandom theo **CC BY-SA** — cần ghi nguồn khi hiển thị lại
- **Dùng `cmcontinue`** để paginate khi category >500 items

---

## Related

- [[MediaWiki API Reference Guide]]
- [[Liqi]]
