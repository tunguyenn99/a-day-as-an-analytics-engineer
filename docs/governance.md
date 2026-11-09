# DAMA-aligned governance operating model

Đây là blueprint áp dụng DAMA-DMBOK, không phải chứng nhận tuân thủ. OpenMetadata là catalog/governance plane, không thay thế quyền truy cập trong PostgreSQL và Storage.

| Knowledge area | Triển khai | Người chịu trách nhiệm / bằng chứng |
|---|---|---|
| Data governance | Domains Acquisition, Engagement, Commerce, Finance, Customer, Product và Shared, owner và steward; phê duyệt thay đổi metric qua PR | Domain owner, CODEOWNERS và PR |
| Data architecture | Landing → bronze → silver → gold → platinum; raw nằm ở S3 | Analytics engineer, dbt lineage |
| Data modeling | Source natural keys, conformed dimensions, atomic facts và explicit mart grains | Model owner, YAML và contracts |
| Data storage & operations | Archive immutable theo hash; artifacts theo run; backup/PITR và restore drill | Platform owner, restore report |
| Data security | Private buckets, SSL, least privilege, schema grants; PII classification | Security steward, access review |
| Data integration | Source contracts, retry/idempotency; watermark/pagination riêng từng API | Source owner, ingestion logs |
| Documents & content | Runbook, glossary và ADR trong repo/catalog | Steward, review hàng quý |
| Reference/master data | Chuẩn hóa currency; quản lý mã khách hàng giữa các nguồn | Business steward, mapping có version |
| Data warehousing & BI | Gold facts, platinum metrics; owner dashboard | Analytics owner, metric definitions |
| Metadata management | Postgres discovery trước; ingest dbt manifest/catalog/results sau | Metadata steward, lineage coverage |
| Data quality | Not-null, uniqueness, FK relationships, ordered funnel, reconciliation và SCD2 overlap | Model owner, dbt test results |

## Bootstrap OpenMetadata

1. Deploy OpenMetadata bằng official Docker/Helm của phiên bản đã chọn. Repo này không tự deploy server, search engine hoặc metadata database. Đặt GitHub variable `OPENMETADATA_VERSION` bằng bản `openmetadata-ingestion` khớp server (ví dụ server 2.0.7 → SDK 2.0.7.x).
2. Lấy JWT của `ingestion-bot` (Settings → Bots), lưu vào secret `OPENMETADATA_JWT`, và đặt `OPENMETADATA_HOST`. Nên tạo PostgreSQL user chỉ đọc cho catalog (USAGE các schema, SELECT, đọc `pg_catalog`) và lưu vào `OPENMETADATA_PGUSER`/`OPENMETADATA_PGPASSWORD`; nếu không có, CD dùng `PG*`.
3. Chạy manual full CD. [scripts/openmetadata_bootstrap.py](../scripts/openmetadata_bootstrap.py) tạo team `analytics-engineering`, các domains, glossary `WebAnalytics` (Session, Pageview, Order, OrderItem, Refund, GrossRevenue, NetRevenue, SessionConversionRate), classification `Sensitivity` (Public, Internal, Confidential, PII) và dashboard `grafana.web-analytics`. Sau đó CD chạy PostgreSQL metadata ingestion rồi đến dbt ingestion; database service do workflow tự tạo theo `OPENMETADATA_SERVICE`.
4. Bổ sung người thật vào team, đặt domain experts và glossary reviewers trong UI. Bootstrap chỉ PUT các trường nó quản lý, nên không ghi đè thành viên team.
5. Khai báo metadata trong dbt: `meta.owner`, `meta.openmetadata.domain`, `meta.openmetadata.tier` cho model/source; `meta.openmetadata.glossary` và `meta.openmetadata.tags` cho cột. Tên mới phải được thêm vào bootstrap; test `test_dbt_meta_references_exist_in_bootstrap` sẽ fail nếu thiếu.
6. Auto CD (slim) lọc table names từ dbt selection, giữ nguyên full manifest để không mất context lineage, và không bật xóa assets trong dbt ingestion. Tên model phải duy nhất toàn project.
7. Tạo quality SLO: 100% platinum có owner/description, test pass trước release; freshness < 26 giờ cho daily run (Prometheus `MedallionDagNoRecentSuccess`, dbt source freshness); review quyền hàng quý. Cấu hình `ALERT_WEBHOOK_URL`/Alertmanager và escalation bằng owner thực tế trước production.

## Giới hạn theo nguồn thật

Nguồn SQL Server web_analytics không có updated_at/CDC; ingestion đọc full bằng keyset batches và kiểm tra row count. Full extraction publish cả 6 bảng trong một transaction; cập nhật/xóa nguồn được phản ánh ở lần publish tiếp theo. READ COMMITTED ở nguồn không đảm bảo consistent point-in-time snapshot khi có concurrent writes. Cần source snapshot isolation hoặc CDC cho dữ liệu giao dịch đang thay đổi.

Products snapshot dùng check strategy theo product_name. SCD2 chỉ phản ánh thay đổi quan sát từ khi pipeline chạy; không dựng lại business history 2012–2015. Datetime nguồn không công bố timezone, vì vậy giữ timestamp nguyên bản. user_id nên được xem là pseudonymous identifier và đánh giá classification trước khi chia sẻ.

Marketing không có spend nên không tính ROI/ROAS. Finance và product mart có refund attribution khác nhau; contracts nằm trong docs/domain-modeling.md. Không tự đánh đồng UTM-tagged traffic là paid.

PostgreSQL transaction không bao trùm toàn bộ dbt graph: CD fail có thể đã cập nhật một số relation dù manifest pointer chưa promote. CD concurrency không khóa cùng DAG production; tránh ghi đồng thời hoặc bổ sung shared lock. S3 completion marker được ghi sau landing DB commit, không phải distributed transaction.
