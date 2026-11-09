# Validation evidence

Đã kiểm tra trực tiếp nguồn SQL Server web_analytics bằng SELECT, và full-extract vào database PostgreSQL 16 local riêng `web_analytics_validation`. Không ghi vào SQL Server, Supabase hay OpenMetadata khi thực hiện lần verification này. Raw archive bị tắt tường minh bằng `archive=False` vì chưa có Storage credentials.

| Source table | Extracted rows |
|---|---:|
| website_sessions | 472,871 |
| website_pageviews | 1,188,124 |
| orders | 32,313 |
| order_items | 40,025 |
| order_item_refunds | 1,731 |
| products | 4 |
| Total | 1,735,068 |

Full `dbt build`: 30 models, 1 snapshot, 177 data tests; PASS=208, WARN=0, ERROR=0, SKIP=0. Các custom tests bao gồm finance/header-items reconciliation, ordered funnel monotonicity, conversion range, unique mart grain và SCD2 overlap.

| Reconciliation | USD |
|---|---:|
| Order header gross revenue | 1,938,509.75 |
| Product/item gross revenue | 1,938,509.75 |
| Total refunds | 85,338.69 |
| Finance net revenue | 1,853,171.06 |
| Product net revenue | 1,853,171.06 |

Marketing mart tổng hợp 472,871 sessions và 32,313 orders, gross revenue khớp orders. Product mart có 40,025 units. Giữ riêng converted_sessions và orders dù dataset hiện quan sát số lượng bằng nhau; synthetic fixture có nhiều orders trong một session để kiểm tra khác biệt này.

Black và SQLFluff pass. 8 Python tests pass khi bật RUN_DB_TESTS trên PostgreSQL local: source contract serialization/validation, CD promotion guards, replay và transaction rollback khi extraction fail sau khi một số bảng đã load. Cosmos DAG import thành công với 33 tasks (ingestion + models + snapshot + test task).

## Kiểm chứng sau khi bổ sung contracts, unit tests và alerting

Các số liệu trên là lần full build với dữ liệu thật trước khi bổ sung model contracts, unit tests, source freshness và metadata OpenMetadata. Sau các thay đổi này, build trên fixture tổng hợp (cùng quy trình CI) ra PASS=213, WARN=0, ERROR=0: 30 models, 1 snapshot, 179 data tests và 3 unit tests. `dbt source freshness` PASS cho 7 sources. 20 Python tests pass, gồm cả test rollback transaction khi bật `RUN_DB_TESTS`. Chưa build lại toàn bộ dữ liệu thật.

Alerting: `promtool check rules` hợp lệ với 5 rules và Prometheus nạp đủ. Khi dừng Airflow có chủ đích, `AirflowSchedulerNotHeartbeating` chuyển sang firing. DAG import trong container với 33 tasks, có `on_failure_callback` và `dagrun_timeout`.

## OpenMetadata ingestion

Đã chạy end-to-end luồng CD full (`dbt build` → `docs generate` → `scripts.metadata_ingest --mode full`) với OpenMetadata server 2.0.7 local, SDK `openmetadata-ingestion` 2.0.7.2 và token của `ingestion-bot`:

| Workflow | Records | Warnings | Errors |
|---|---:|---:|---:|
| PostgreSQL metadata | 45 | 0 | 0 |
| dbt | 130 | 0 | 0 |

- 38/38 tables (landing, bronze, silver, gold, platinum, history) có description; mọi bảng do dbt quản lý có đủ mô tả cột, owner `analytics-engineering`, domain và tier (Tier1 platinum, Tier2 gold, Tier3 source/history).
- Glossary terms gắn vào cột (`GrossRevenue`, `NetRevenue`, `SessionConversionRate`, `Session`, `Order`…); `user_id` được gắn `Sensitivity.Confidential` ở silver và gold.
- Mỗi model có raw SQL và compiled SQL (dataModel DBT) cùng đường dẫn file.
- Lineage của `mart_finance_daily`: landing → bronze → silver → gold → platinum → dashboard `grafana.web-analytics`.
- Kết quả dbt tests được ingest thành test cases, ví dụ 10/10 Success cho `mart_finance_daily`.
- Slim mode chỉ lọc đúng `^mart_finance_daily$` khi model đó thay đổi, và bỏ qua dbt ingestion khi không có thay đổi.

Đây là kiểm chứng trên server local; server, bot và secrets production vẫn cần cấu hình riêng.

## Capacity

Database local sau full build khoảng 985 MB: landing JSON 627 MB, silver 136 MB, gold 211 MB, platinum 3.5 MB; snapshot nhỏ. Đây là số đo instance local, không phải cam kết footprint Supabase, và chưa gồm peak storage của staging/rebuild trên cloud.

[Supabase Free có quota database 500 MB](https://supabase.com/docs/guides/platform/billing-on-supabase). Thiết kế materialization hiện tại vượt quota khi dùng toàn bộ dataset. Trước full deployment cần chọn dung lượng phù hợp hoặc thiết kế storage gọn hơn (raw chỉ lưu S3 và typed landing, giảm materialized copies); không âm thầm cắt bớt source rows. Chưa có benchmark runtime trên Supabase nano.

## Chưa xác minh bên ngoài

- PostgreSQL Supabase session-pooler credentials/network.
- Supabase S3 upload và completion markers trên bucket thật.
- OpenMetadata production server, bot auth và secrets (luồng ingestion đã kiểm chứng trên server 2.0.7 local).
- GitHub-hosted CI/CD execution và containerized full platform startup; local đã kiểm tra compose config và DAG import.
