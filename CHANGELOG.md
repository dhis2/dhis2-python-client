# 📜 Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.0] - 2025-09-09
### ✨ Added
- **Command-line interface (`dhis2-client`)**  
  - Subcommands:  
    - `system-info` — fetch `/api/system/info`  
    - `get` — generic GET with paging (`--all`, `--page-size`)  
    - `period` — validate and format period strings  
- **Authentication flags**: `--base-url`, `--username`, `--password` (hidden prompt), `--token`  
- **Multiple output formats**: `json`, `yaml`, `table`, `ndjson`  
- **CLI extras** (`typer`, `rich`, `pyyaml`) in `pyproject.toml`  

### 📖 Documentation
- Full **README.md** update with CLI usage, examples, and configuration layers  

### 🧪 Tests
- Added CLI smoke tests with Typer’s `CliRunner`  
- Verified paging and output formats  

### 🔧 Internal
- New CLI module under `src/dhis2_client/cli/`  
- Maintains Python **3.8+** support  

---

## [v0.1.0] - 2025-??-??
### 🎉 Initial release
- Async client with **httpx** + **Pydantic v2**  
- Paging helpers and period utilities  
- Typed models for common DHIS2 resources  
- Unit + integration tests  

## [0.3.0] - 2025-09-11
### Added
- Programmatic + environment-based logging configuration.
- Defaults to `WARNING` log level for quieter output.

### Changed
- Integration tests improved with better conflict summary.
- Minor refactors and lint fixes.
