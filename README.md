# dhis2-client 🌀

> **Async DHIS2 Web API client** (Python **3.8+**) with **httpx**, **Pydantic v2**, **structured logging**, and **paging**.  
> Includes **period validation/formatting**, clean **typed models**, and a full **unit + integration** test suite.

<p align="center">
  <img alt="status" src="https://img.shields.io/badge/status-stable-blue"/>
  <img alt="python" src="https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="pydantic" src="https://img.shields.io/badge/pydantic-v2-FF4D4D"/>
  <img alt="httpx" src="https://img.shields.io/badge/httpx-async-7D8AFF"/>
  <img alt="license" src="https://img.shields.io/badge/license-MIT-success"/>
</p>

## 🗂️ Table of Contents
- [✨ Overview](#overview)
- [🚀 Features](#features)
- [📋 Requirements](#requirements)
- [⚙️ Installation](#installation)
- [🔑 Configuration](#configuration)
- [💡 Usage](#usage)
  - [Create a Client](#create-a-client)
  - [Generic Endpoints](#generic-endpoints)
  - [Typed Helpers](#typed-helpers)
  - [Paging](#paging)
  - [Periods](#periods)
- [📖 API Reference](#api-reference)
- [📝 Logging](#logging)
- [❗ Errors](#errors)
- [🧪 Testing](#testing)
  - [Unit](#unit)
  - [Integration](#integration)
- [📂 Project Layout](#project-layout)
- [🙋 FAQ](#faq)
- [🤝 Contributing](#contributing)
- [📜 License](#license)

<a id="overview"></a>
## ✨ Overview

A small, focused **async** client for the **DHIS2 Web API**:
- **Generic** HTTP helpers so you can hit any path.
- **Typed** models for common resources.
- **Paging** and **period** helpers out-of-the-box.

<a id="features"></a>
## 🚀 Features

- ⚡ **Async HTTP** via `httpx.AsyncClient`
- ✅ **Pydantic v2** models (strict request validation, safe response parsing)
- 🧱 **Structured logging** with `structlog` (JSON output)
- 📑 **Paging helpers** using `pager.page` / `pageCount`
- 📅 **Period validation & formatting** (subset of DHIS2 types)
- 🧪 **Tests**: unit + integration (with `.env` and optional pinned UIDs)

<a id="requirements"></a>
## 📋 Requirements

- Python **3.8+**
- A running DHIS2 instance for integration tests

<a id="installation"></a>
## ⚙️ Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt   # for tests
```

<a id="configuration"></a>
## 🔑 Configuration

Put credentials and options in `.env` (see `.env.example`):

```env
DHIS2_BASE_URL=http://localhost:8080
DHIS2_USERNAME=admin
DHIS2_PASSWORD=district
# or DHIS2_TOKEN=your_api_token

DHIS2_TIMEOUT=30
VERIFY_SSL=true
LOG_LEVEL=INFO

# Optional pins for stable integration runs:
# TEST_DATASET_UID=lyLU2wR22tC
# TEST_OU_UID=ImspTQPwCqd
# TEST_DE_UID=fbfJHSPpUQD
```

> The tests can auto-pick **default COC/AOC**, so you typically only need DS/OU/DE pins.

<a id="usage"></a>
## 💡 Usage

<a id="create-a-client"></a>
### Create a Client

```python
import asyncio
from dhis2_client import DHIS2AsyncClient, Settings

async def main():
    settings = Settings()  # loads from .env
    async with DHIS2AsyncClient.from_settings(settings) as client:
        info = await client.get_system_info()
        print(info.version)

asyncio.run(main())
```

<a id="generic-endpoints"></a>
### Generic Endpoints

```python
await client.get("/api/organisationUnits", params={"pageSize": 5})
await client.post_json("/api/dataElements", {"name":"My DE","shortName":"MDE","domainType":"AGGREGATE","valueType":"INTEGER"})
```

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

<a id="paging"></a>
### Paging

```python
async for page in client.iter_data_elements(fields=["id","name"], page_size=500):
    for de in page:
        print(de.id, de.name)
```

<a id="periods"></a>
### Periods

```python
from datetime import date
from dhis2_client.models import validate_period, format_period

validate_period("Monthly", "202501")          # ok
format_period("Weekly", date(2025, 1, 15))    # "2025W03"
```

<a id="api-reference"></a>
## 📖 API Reference

### 🔧 System
- `get_system_info()` → `SystemInfo`

### 🏢 Organisation Units
- `get_organisation_units(fields, page_size=100, paging=True)`
- `iter_organisation_units(fields, page_size=100)`
- `list_all_organisation_units(fields, page_size=100)`

### 📊 Data Elements
- `get_data_elements(fields, page_size=100, paging=True)`
- `iter_data_elements(fields, page_size=100)`
- `list_all_data_elements(fields, page_size=100)`

### 📦 Data Sets
- `get_data_sets(fields, page_size=100, paging=True)`
- `iter_data_sets(fields, page_size=100)`
- `list_all_data_sets(fields, page_size=100)`

### 📝 Data Value Sets
- `post_data_value_set(dvs: DataValueSet, import_strategy="CREATE"|"DELETE", dry_run=False)`

### 🌐 Generic Endpoints
- `get(path, params=None)`
- `post_json(path, payload)`
- `put_json(path, payload)`
- `delete(path)`

### 📅 Period Utilities
- `validate_period(period_type, period_str)`
- `format_period(period_type, date_obj)`

<a id="logging"></a>
## 📝 Logging

Emits compact JSON:
```json
{"event":"http.request","method":"GET","path":"/api/system/info","request_id":"..."}
{"event":"http.response","status":200,"path":"/api/system/info","request_id":"..."}
```

<a id="errors"></a>
## ❗ Errors

HTTP errors raise typed exceptions, e.g. `NotFound`, `Conflict`.  
Payload (if parsed) is attached to `details` for debugging.

<a id="testing"></a>
## 🧪 Testing

<a id="unit"></a>
### Unit
```bash
pytest -q tests/unit
```

<a id="integration"></a>
### Integration
```bash
# Non-destructive
pytest -q -m integration

# With writes
export ALLOW_DHIS2_MUTATIONS=true
pytest -q -m integration
```

<a id="project-layout"></a>
## 📂 Project Layout

```
├── LICENSE
├── mypy.ini
├── pyproject.toml
├── pytest.ini
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── src
│   └── dhis2_client
│       ├── __init__.py
│       ├── client.py
│       ├── exceptions.py
│       ├── logging_conf.py
│       ├── settings.py
│       └── models
│           ├── __init__.py
│           ├── collections.py
│           ├── common.py
│           ├── data_element.py
│           ├── data_set.py
│           ├── data_value.py
│           ├── data_value_set.py
│           ├── organisation_unit.py
│           ├── periods.py
│           └── system.py
└── tests
    ├── integration
    │   ├── conftest.py
    │   ├── test_live_data_values.py
    │   ├── test_live_endpoints.py
    │   ├── test_live_full_stack.py
    │   └── test_live_mutations.py
    └── unit
        ├── test_endpoints.py
        ├── test_models.py
        ├── test_paging.py
        └── test_periods.py
```

<a id="faq"></a>
## 🙋 FAQ

- **Why generic endpoints?** Flexibility; typed wrappers where helpful.
- **Python 3.8 quirks?** No PEP 604 unions; `isocalendar()` handled explicitly.

<a id="contributing"></a>
## 🤝 Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the onboarding guide, testing strategy, and contribution rules.

<a id="license"></a>
## 📜 License

MIT
