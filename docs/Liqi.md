---
categories:
  - "[[Projects]]"
subjects:
  - "[[Data Science & ML]]"
type: project
status: active
priority: p2
deadline:
repo: ""
created: 2026-08-19
---

# Liqi

**Goal:** Xây dựng một hệ thống phân tích và hỗ trợ draft cho Liên Quân Mobile, có thể thu thập dữ liệu trận đấu, khai phá quan hệ giữa các tướng và đưa ra dự đoán hoặc gợi ý cấm/chọn dựa trên dữ liệu.

---

## Project Files

```base
filters:
  and:
    - file.hasLink(this.file)
properties:
  file.name:
    displayName: Title
  note.categories:
    displayName: Category
  note.status:
    displayName: Status
views:
  - type: table
    name: All
    order:
      - file.name
      - categories
      - status
```

---

## Milestones & Tasks

### Iteration 1 — Wiki (LiqiWiki) _[Sprint hiện tại]_

> Mục tiêu: Crawling dữ liệu tướng, trang bị, kỹ năng từ AOV Fandom wiki và hiển thị trên web app.

- [ ] Setup monorepo và cấu trúc project (Next.js + NestJS + FastAPI + PostgreSQL)
- [ ] Xây crawler dùng MediaWiki API — category members, wikitext parsing, Cargo query
- [ ] ETL: chuẩn hóa dữ liệu tướng, trang bị, kỹ năng, bản đồ, chế độ chơi
- [ ] Lưu vào PostgreSQL (schema `data`)
- [ ] API endpoints đọc dữ liệu wiki (NestJS)
- [ ] Web app hiển thị danh sách tướng, chi tiết trang bị, kỹ năng
- [ ] Theo dõi cập nhật wiki (recent changes, revision history)
- Chi tiết endpoint: [[Liqiwiki-Fandom_endpoint]]
- Chi tiết crawler: [[Liqi-crawling]]

### Iteration 2 — Phân tích combo (Association Rules)

> Mục tiêu: Khai phá combo tướng có tỉ lệ thắng cao và chuỗi trang bị tối ưu.

- [ ] Thu thập dữ liệu trận đấu (match results, team compositions)
- [ ] Chuẩn hóa và lưu trữ dữ liệu trận
- [ ] Chạy FP-Growth / Apriori theo dataset/patch
- [ ] Lưu kết quả (support, confidence, lift) vào PostgreSQL
- [ ] API đọc kết quả combo (NestJS)
- [ ] Web app hiển thị combo phổ biến, tỉ lệ thắng, filter theo tướng/patch
- Owner: Đại

### Iteration 3 — Dự đoán kết quả trận đấu (Match Prediction)

> Mục tiêu: Dự đoán đội thắng dựa trên đội hình pick tướng.

- [ ] Tạo features từ dữ liệu tướng, đội hình, tương khắc
- [ ] Train baseline (XGBoost / LightGBM / Random Forest)
- [ ] Đánh giá model, lưu model artifacts
- [ ] FastAPI inference endpoint
- [ ] NestJS gọi FastAPI, trả kết quả cho web app
- [ ] Web app hiển thị xác suất thắng, phân tích features quan trọng
- Owner: An

### Iteration 4 — Gợi ý cấm/chọn (Draft Recommender)

> Mục tiêu: Gợi ý lượt pick/counter-pick tiếp theo dựa trên trạng thái draft.

- [ ] Tính synergy, counter statistics từ dữ liệu lịch sử
- [ ] Baseline: xếp hạng tướng theo vai trò còn thiếu, synergy đồng đội, counter đối phương
- [ ] FastAPI inference endpoint
- [ ] Web app mô phỏng draft, hiển thị gợi ý theo lượt
- [ ] (Nâng cấp sau) Train GNN khi có đủ dữ liệu
- Owner: Trọng

---

## Data

- **Meta và chỉ số tướng:** Trang chủ Garena và AOV Tracker
- **Giải đấu chuyên nghiệp:** ĐTDV, AIC và AWC

Chi tiết crawler: [[Liqi-crawling]]

## Features

| Feature                                                          | Thuật toán gợi ý                               | Mục tiêu đầu ra                                                                              |
| ---------------------------------------------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------- |
| LiqiPred - Dự đoán kết quả trận đấu                              | XGBoost, LightGBM, Random Forest               | Dự đoán đội thắng dựa trên đội hình, tương khắc chất tướng và chênh lệch tài nguyên ban đầu. |
| LiqiAsso - Phân tích tập phổ biến và luật kết hợp                | Apriori, FP-Growth                             | Khai phá combo tướng có tỉ lệ thắng cao hoặc chuỗi lên trang bị tối ưu.                      |
| LiqiReco - Hệ thống gợi ý cấm/chọn                               | Collaborative Filtering, Graph Neural Networks | Gợi ý lượt pick/counter-pick tiếp theo dựa trên các lượt pick trước đó của hai đội.          |
| LiqiWiki - Thu thập và hiển thị dữ liệu tướng, trang bị, kỹ năng | MediaWiki API, Cargo query                     | Crawling dữ liệu từ AOV Fandom wiki, chuẩn hóa và hiển thị trên web app.                     |

## References

- [[Liqiwiki-Fandom_endpoint]]

---

## Quick Links & Resources

- **Repository:** [liqily](https://github.com/githubcuaan/liqily)
- **Documentation:** [[Liqi-crawling]]

---

## Log & Notes

- 2026-08-19: Khởi tạo dự án và phân chia các phase chính.
