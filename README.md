# 🚀 dhis2-python-client

> **Async DHIS2 Web API client** (Python **3.10+**) with **httpx**, **Pydantic v2**, **structured logging**, and **paging**.  
> Includes **period validation/formatting**, clean **typed models**, a full **unit + integration** test suite, and an optional **CLI**.

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-stable-blue"/>
  <img alt="python" src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="pydantic" src="https://img.shields.io/badge/pydantic-v2-FF4D4D"/>
  <img alt="httpx" src="https://img.shields.io/badge/httpx-async-7D8AFF"/>
  <img alt="license" src="https://img.shields.io/badge/license-MIT-success"/>
</p>

---

## 🗂️ Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Create a Client](#create-a-client)
  - [Generic Endpoints](#generic-endpoints)
  - [Typed Helpers](#typed-helpers)
  - [Paging](#paging)
  - [Periods](#periods)
  - [CLI](#cli)
- [API Reference](#api-reference)
- [Logging](#logging)
- [Errors](#errors)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

<a id="overview"></a>
## ✨ Overview

A small, focused **async** client for the **DHIS2 Web API**:
- **Generic** HTTP helpers so you can hit any path.
- **Typed** models for common resources.
- **Paging** and **period** helpers out-of-the-box.
- **CLI** for quick one-liners and automation.

---

<a id="features"></a>
## 🚀 Features

- ⚡ **Async HTTP** via `httpx.AsyncClient`
- ✅ **Pydantic v2** models (strict request validation, safe response parsing)
- 🧱 **Structured logging** with `structlog` (JSON output)
- 📑 **Paging helpers** using `pager.page` / `pageCount`
- 📅 **Period validation & formatting** (subset of DHIS2 types)
- 💻 **CLI** built with `typer` + `rich`
- 🧪 **Tests**: unit + integration (with `.env` and optional pinned UIDs)

---

<a id="requirements"></a>
## 📋 Requirements

- Python **3.10+**
- A running DHIS2 instance for integration tests

---

<a id="installation"></a>
## ⚙️ Installation

### Library only
```bash
pip install dhis2-python-client
```

### Library + CLI
```bash
pip install "dhis2-python-client[cli]"
```
👉 This installs the `dhis2-client` executable along with `typer`, `rich`, and `pyyaml`.

### Development install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
pip install -e ".[cli]"
```

---

<a id="configuration"></a>
## 🔑 Configuration

Put credentials and options in a `.env` file in the root folder:

```env
DHIS2_BASE_URL=http://localhost:8080
DHIS2_USERNAME=admin
DHIS2_PASSWORD=district
#or DHIS2_TOKEN=your_api_token

DHIS2_TIMEOUT=30
VERIFY_SSL=true
LOG_LEVEL=INFO
```

> CLI and library also support layered config: system TOML, user TOML, `.env`, environment variables, then CLI flags.

---

<a id="usage"></a>
## 💡 Usage

---

<a id="create-a-client"></a>
### Create a Client

```python
import asyncio
from dhis2_client import DHIS2AsyncClient, Settings

async def main():
    settings = Settings()  # loads from env/.env
    async with DHIS2AsyncClient.from_settings(settings) as client:
        info = await client.get_system_info()
        print(info.version)

asyncio.run(main())
```

---

<a id="generic-endpoints"></a>
### Generic Endpoints

```python
await client.get("/api/organisationUnits", params={"pageSize": 5})
await client.post_json("/api/dataElements", {"name": "My DE", "shortName": "MDE", "domainType": "AGGREGATE", "valueType": "INTEGER"})
```

---

<a id="typed-helpers"></a>
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
await client.post_data_value_set(payload, import_strategy="CREATE")
```

---

<a id="paging"></a>
### Paging

```python
async for page in client.iter_data_elements(fields=["id","name"], page_size=500):
    for de in page:
        print(de.id, de.name)
```

---

<a id="periods"></a>
### Periods

```python
from datetime import date
from dhis2_client.models import validate_period, format_period

validate_period("Monthly", "202501")          # ok
format_period("Weekly", date(2025, 1, 15))    # "2025W03"
```

---

<a id="cli"></a>
### Command-line interface (CLI)

Install with CLI extras:
```bash
pip install "dhis2-python-client[cli]"
```

Usage examples:
```bash
# System info
dhis2-client system-info --output table

# Generic GET with paging
dhis2-client --base-url https://play.dhis2.org/dev --username admin --password district \
  get /api/dataElements --fields id --fields name --all --output ndjson

# Safer: prompt for password
dhis2-client --base-url https://play.dhis2.org/dev --username admin system-info
# Password: ****

# Token usage
dhis2-client --base-url https://play.dhis2.org/dev --token $MYTOKEN system-info

# Period helpers
dhis2-client period validate Monthly 202501
```

---

<a id="api-reference"></a>
## 📖 API Reference

### System
- `get_system_info()` → `SystemInfo`

### Organisation Units
- `get_organisation_units(fields, page_size=100, paging=True)`
- `iter_organisation_units(fields, page_size=100)`
- `list_all_organisation_units(fields, page_size=100)`

### Data Elements
- `get_data_elements(fields, page_size=100, paging=True)`
- `iter_data_elements(fields, page_size=100)`
- `list_all_data_elements(fields, page_size=100)`

### Data Sets
- `get_data_sets(fields, page_size=100, paging=True)`
- `iter_data_sets(fields, page_size=100)`
- `list_all_data_sets(fields, page_size=100)`

### Data Value Sets
- `post_data_value_set(dvs: DataValueSet, import_strategy="CREATE"|"DELETE", dry_run=False)`

### Generic Endpoints
- `get(path, params=None)`
- `post_json(path, payload)`
- `put_json(path, payload)`
- `delete(path)`

### Period Utilities
- `validate_period(period_type, period_str)`
- `format_period(period_type, date_obj)`

---

<a id="logging"></a>
## 📝 Logging

By default, `dhis2-client` only logs **warnings and errors**.

You can increase verbosity with either:

**Control log level via environment variable**
```bash
export LOG_LEVEL=INFO

```
**Or programmatically**
```python
from dhis2_client.logging_conf import configure_logging

# Enable DEBUG/INFO logs
configure_logging("INFO")

# Include underlying httpx/respx request logs as well
configure_logging("DEBUG", include_httpx=True)
```


---

<a id="errors"></a>
## ❗ Errors

HTTP errors raise typed exceptions, e.g. `NotFound`, `Conflict`.  
Payload (if parsed) is attached to `details` for debugging.

---

<a id="faq"></a>
## 🙋 FAQ

- **Why generic endpoints?** Flexibility; typed wrappers where helpful.
- **Why a CLI?** For quick inspection, automation, and integration with shell pipelines.

---

<a id="contributing"></a>
## 🤝 Contributing

See **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** for the onboarding guide, testing strategy, and contribution guidelines.

---

<a id="license"></a>
## 📜 License
