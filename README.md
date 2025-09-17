# dhis2-python-client

> Async & Sync DHIS2 Web API client (Python 3.10+) with httpx, Pydantic v2, structured logging, and paging.  
> Includes period validation/formatting, clean typed models, a full unit + integration test suite, and a powerful CLI (sync or async).

![status](https://img.shields.io/badge/status-active-brightgreen)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![pydantic](https://img.shields.io/badge/pydantic-v2-ff69b4)
![httpx](https://img.shields.io/badge/httpx-async%20%26%20sync-6f42c1)
![license](https://img.shields.io/badge/license-BSD--3--Clause-lightgrey)

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
  - [Logging](#logging)
  - [Return Types](#return-types)
- [Usage](#-usage)
  - [Create a Client (Sync)](#create-a-client-sync)
  - [Create a Client (Async)](#create-a-client-async)
  - [Generic Endpoints](#generic-endpoints)
  - [Typed Helpers](#typed-helpers)
  - [Paging](#paging)
  - [Periods](#periods)
- [CLI](#-cli)
  - [CLI Cheat Sheet](#cli-cheat-sheet)
  - [Examples](#examples)
- [API Reference](#-api-reference)
- [Logging](#-logging)
- [Errors](#-errors)
- [FAQ](#-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Overview

A small, focused client for the DHIS2 Web API supporting **both Sync and Async** programming styles:

- Generic HTTP helpers so you can hit any path.
- Typed models for common resources **or** raw dict/JSON (your choice).
- Paging and period helpers out-of-the-box.
- CLI for quick one-liners and automation (**sync or async engine**).

---

## 🚀 Features

- ⚡ **Async & Sync** HTTP via `httpx.AsyncClient` and `httpx.Client`
- ✅ **Pydantic v2** models (strict request validation, safe response parsing)
- 🧩 **Return type control**: default **dict/JSON**; opt-in Pydantic (per-call or global)
- 🧭 Paging helpers using `pager.page` / `pageCount`
- 📅 Period validation & formatting (subset of DHIS2 types)
- 🛠 **CLI** built with `typer` + `rich` (supports `--engine sync|async`, default = sync)
- 🧪 Tests: unit + integration (with `.env` and optional pinned UIDs)
- 🧰 Structured logging with `structlog` (JSON output)

---

## 📋 Requirements

- Python 3.10+
- A running DHIS2 instance for integration tests

---

## 📦 Installation

### Library only

```bash
pip install dhis2-python-client
```

### Library + CLI

```bash
pip install "dhis2-python-client[cli]"
```

This installs the `dhis2-client` executable along with `typer`, `rich`, and `pyyaml`.

### Development install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
pip install -e ".[cli]"
```

---

## ⚙️ Configuration

Put credentials and options in a `.env` file in the root folder:

```
DHIS2_BASE_URL=http://localhost:8080
DHIS2_USERNAME=admin
DHIS2_PASSWORD=district
# or DHIS2_TOKEN=your_api_token

DHIS2_TIMEOUT=30
VERIFY_SSL=true
LOG_LEVEL=WARNING
# Return type default (False -> dict/JSON, True -> Pydantic)
RETURN_MODELS=false
```

CLI and library also support layered config: system TOML, user TOML, `.env`, environment variables, then CLI flags.

### Logging

Default level = **WARNING** ⚠️. You can configure via `Settings` or env.

```python
from dhis2_client import Settings

settings = Settings(
    base_url="http://localhost:8080",
    username="admin",
    password="district",
    log_level="INFO",  # DEBUG | INFO | WARNING | ERROR | CRITICAL
)
```

### Return Types

By default, methods return **plain `dict` (JSON)** ✅. This is controlled globally via the `Settings.return_models` flag:

- `return_models=False` (default) → always return dict/JSON unless overridden.  
- `return_models=True` → return Pydantic models by default.  

You can also override **per-call** with the `as_dict` flag.

```python
# dict (default)
info = client.get_system_info()
print(info["version"])

# Pydantic model
info_m = client.get_system_info(as_dict=False)
print(info_m.version)

# Global opt-in to models
settings = Settings(..., return_models=True)
client = DHIS2Client.from_settings(settings)
info = client.get_system_info()  # model
```

---

## 🐍 Usage

### Create a Client (Sync)

```python
from dhis2_client import DHIS2Client, Settings

settings = Settings(base_url="http://localhost:8080", username="admin", password="district")
with DHIS2Client.from_settings(settings) as client:
    info = client.get_system_info()  # dict by default
    print(info["version"])
```

### Create a Client (Async)

```python
import asyncio
from dhis2_client import DHIS2AsyncClient, Settings

async def main():
    settings = Settings(base_url="http://localhost:8080", username="admin", password="district")
    async with DHIS2AsyncClient.from_settings(settings) as client:
        info = await client.get_system_info()  # dict by default
        print(info["version"])
asyncio.run(main())
```

### Generic Endpoints

```python
# sync
client.get("/api/organisationUnits", params={"pageSize": 5})
client.post_json("/api/dataElements", {"name": "My DE", "shortName": "MDE", "domainType": "AGGREGATE", "valueType": "INTEGER"})

# async
await client.get("/api/organisationUnits", params={"pageSize": 5})
await client.post_json("/api/dataElements", {"name": "My DE", "shortName": "MDE", "domainType": "AGGREGATE", "valueType": "INTEGER"})
```

### Typed Helpers

```python
from datetime import date
from dhis2_client.models import DataValueSet, DataValue, format_period

period = format_period("Monthly", date.today())
payload = DataValueSet(
    dataSet="lyLU2wR22tC",
    period=period,
    orgUnit="ImspTQPwCqd",
    dataValues=[DataValue(dataElement="fbfJHSPpUQD", orgUnit="ImspTQPwCqd", period=period, value="1")]
)

# sync
client.post_data_value_set(payload, import_strategy="CREATE")

# async
await client.post_data_value_set(payload, import_strategy="CREATE")
```

### Paging

```python
# async iteration
async for page in client.iter_data_elements(fields=["id","name"], page_size=500):
    for de in page:
        # 'de' is dict by default (or model if return_models=True / as_dict=False)
        print(de.get("id"), de.get("name"))
```

### Periods

```python
from datetime import date
from dhis2_client.models import validate_period, format_period

validate_period("Monthly", "202501")          # ok
format_period("Weekly", date(2025, 1, 15))    # "2025W03"
```

---

## 🖥 CLI

Install with CLI extras:

```bash
pip install "dhis2-python-client[cli]"
```

The CLI supports **sync or async** via `--engine` (default = sync) and can output **table | json | yaml**.

### CLI Cheat Sheet

| Group              | Purpose                                       |
|--------------------|-----------------------------------------------|
| 🔧 `system`        | System info, ping                             |
| 🌐 `http`          | Raw GET/POST/PUT/DELETE to any path           |
| 📊 `metadata`      | Generic CRUD for all metadata collections     |
| 👤 `users`         | Manage users                                  |
| 📈 `data-values`   | Get/upsert/delete a single data value         |
| 📦 `data-value-sets` | Import/export full sets of data values       |
| 📤 `bulk`          | Bulk JSON upload (events, TEIs, enrollments)  |

### Examples

```bash
# System info (sync, JSON)
dhis2-client system info   --base-url http://localhost:8080 --username admin --password district   --output json

# System info (async, JSON)
dhis2-client system info   --base-url http://localhost:8080 --username admin --password district   --engine async --output json

# Search metadata (async)
dhis2-client metadata search dataElements   --base-url http://localhost:8080 --username admin --password district   --engine async --filter name:ilike:malaria --fields id --fields name --output table

# Create metadata from file
dhis2-client metadata create organisationUnits   --base-url http://localhost:8080 --username admin --password district   --json @orgunit.json

# Users: list
dhis2-client users list   --base-url http://localhost:8080 --username admin --password district   --fields id --fields username --output table

# Data value upsert
dhis2-client data-values upsert   --de DeUid --pe 202401 --ou OuUid --value 42   --base-url http://localhost:8080 --username admin --password district
```

---

## 📚 API Reference

### System
- `get_system_info()` → `dict` (default) or Pydantic with `as_dict=False`

### Organisation Units
- `get_organisation_units(fields, page_size=100, paging=True, as_dict=False)`
- `iter_organisation_units(fields, page_size=100, as_dict=False)`
- `list_all_organisation_units(fields, page_size=100, as_dict=False)`

### Data Elements
- `get_data_elements(fields, page_size=100, paging=True, as_dict=False)`
- `iter_data_elements(fields, page_size=100, as_dict=False)`
- `list_all_data_elements(fields, page_size=100, as_dict=False)`

### Data Sets
- `get_data_sets(fields, page_size=100, paging=True, as_dict=False)`
- `iter_data_sets(fields, page_size=100, as_dict=False)`
- `list_all_data_sets(fields, page_size=100, as_dict=False)`

### Data Value Sets
- `post_data_value_set(dvs: DataValueSet | dict, import_strategy="CREATE"|"DELETE", dry_run=False)`

### Generic Endpoints
- `get(path, params=None)`
- `post_json(path, payload)`
- `put_json(path, payload)`
- `delete(path)`

### Period Utilities
- `validate_period(period_type, period_str)`
- `format_period(period_type, date_obj)`

---

## 📜 Logging

By default, the library logs **WARNING** and above. Increase verbosity with either:

**Environment variable**

```bash
export DHIS2_LOG_LEVEL=INFO
```

**Programmatically**

```python
from dhis2_client.logging_conf import configure_logging
configure_logging(level="INFO")
```

**Via Settings**

```python
from dhis2_client import Settings
settings = Settings(..., log_level="INFO")
```

---

## ❗ Errors

HTTP errors raise typed exceptions, e.g. `NotFound`, `Conflict`.  
Payload (if parsed) is attached to `details` for debugging.

---

## ❓ FAQ

- Why generic endpoints? Flexibility; typed wrappers where helpful.
- Why a CLI? For quick inspection, automation, and integration with shell pipelines.
- Why dict by default? Interop + performance; opt into models when you need type safety.

---

## 🤝 Contributing

See `DEVELOPER_GUIDE.md` for the onboarding guide, testing strategy, and contribution guidelines.

---

## 📄 License

BSD-3-Clause
