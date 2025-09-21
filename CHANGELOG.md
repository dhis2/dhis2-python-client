# Changelog

## [0.1.0] - 2025-09-21
### Added
- Sync `DHIS2Client` using httpx (dict/JSON only).
- Stdlib JSON logging via `ClientSettings`.
- Clean paging (`list_paged`, `fetch_all`).
- Resources: Users (read-only), OrgUnits (CRUD + geojson), DataElements (CRUD),
  DataSets (CRUD), DataValues (single + sets), Analytics (read), System info.
- Unit tests (respx) + live integration tests (guarded by env).
