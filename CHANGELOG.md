# Changelog

## [0.3.1] - 2026-04-14
### Changed
- Corrected release wording from "Centrlized" to "Centralized".
- Added separate `connect_timeout` control (default `60s`) while keeping `timeout` for read/write/pool (default `30s`).

## [0.1.0] - 2025-09-21
### Added
- Sync `DHIS2Client` using httpx (dict/JSON only).
- Stdlib JSON logging via `ClientSettings`.
- Clean paging (`list_paged`, `fetch_all`).
- Resources: Users (read-only), OrgUnits (CRUD + geojson), DataElements (CRUD),
  DataSets (CRUD), DataValues (single + sets), Analytics (read), System info.
- Unit tests (respx) + live integration tests (guarded by env).

## [0.3.0] - 2025-10-08
### Added
- Analytics: latest_period_for_level(de_uid, level) using /api/dataValueSets with calendar-aware windows.
- Utils: calendar_year_bounds, calendar_year_bounds_for, period_key, period_start_end, next_period_id.
### Changed
- Default dependency: convertdate>=2.4 for multi-calendar support.
- HTTP timeout controls: added `connect_timeout` (default 60s) while keeping `timeout` for read/write/pool (default 30s).
### Validation
- Error if data element is linked to datasets with mixed periodType.
