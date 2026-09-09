# M2 Read-only API Contract V1

Version: `m2-read-only-api-v1.0`.

All data endpoints require an explicit successful `publication_id`; one response never combines publications. Lists are server-paginated with `page_size` clamped to 1–100 and return `publication_id`, `page`, `page_size`, `total`, and `items`. The browser increments a request epoch on date change and ignores late responses from an earlier epoch.

Read endpoints: `GET /api/publications`, `/api/dashboard`, `/api/sectors`, `/api/stocks`, `/api/queues`, `/api/evidence`, `/api/identity`, and `/api/linkage`. M2 exposes no write endpoint. Errors return `code`, Chinese `message`, `retryable`, and `next_action`. The service binds to `127.0.0.1` by default and queries DuckDB read-only.

The dashboard reports selected date, actual input date, latest successful publication date, and the bound publication identity. Outputs are explanatory research results, not probability claims, trading advice, or automated trading instructions.
