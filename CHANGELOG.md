# Changelog

## [0.3.2] - 2026-10-05
### Added
- `LICENSE` file (BSD-3-Clause), `py.typed` marker, and PyPI metadata (classifiers, URLs, keywords).
- GitHub Actions: tests and lint on every push and pull request; publish to PyPI on a `v*` tag through trusted publishing.
### Changed
- The `dev` extra now installs everything the test suite needs (`respx`, `python-dotenv`); `matplotlib` moved to an `examples` extra.
- Lint clean under the repository's ruff configuration.
- First release on PyPI: `pip install dhis2-client`.

## [0.3.1] - 2026-04-14
### Changed
- Corrected release wording from "Centrlized" to "Centralized".
- Added separate `connect_timeout` control (default `60s`) while keeping `timeout` for read/write/pool (default `30s`).

## [0.3.0] - 2025-10-08
### Added
- Analytics: latest_period_for_level(de_uid, level) using /api/dataValueSets with calendar-aware windows.
- Utils: calendar_year_bounds, calendar_year_bounds_for, period_key, period_start_end, next_period_id.
### Changed
- Default dependency: convertdate>=2.4 for multi-calendar support.
- HTTP timeout controls: added `connect_timeout` (default 60s) while keeping `timeout` for read/write/pool (default 30s).
### Validation
- Error if data element is linked to datasets with mixed periodType.

## [0.2.0] - 2025-10-01
### Added
- Sharing: read and set public access, user and user-group accesses on metadata objects.
- User organisation-unit scope management (capture, data view, tracked-entity search).

## [0.1.0] - 2025-09-21
### Added
- Sync `DHIS2Client` using httpx (dict/JSON only).
- Stdlib JSON logging via `ClientSettings`.
- Clean paging (`list_paged`, `fetch_all`).
- Resources: Users (read-only), OrgUnits (CRUD + geojson), DataElements (CRUD),
  DataSets (CRUD), DataValues (single + sets), Analytics (read), System info.
- Unit tests (respx) + live integration tests (guarded by env).
