# DHIS2 Python Client 🐍✨

A modern Python client and CLI for [DHIS2](https://dhis2.org).  
Supports both **sync** and **async** engines, with flexible return types (**dict/JSON or Pydantic models**) and a powerful **CLI** for administrators, developers, and data managers.

---

## 📑 Table of Contents

- [Installation](#-installation)
- [Configuration](#-configuration)
  - [Logging](#logging)
  - [Return Types](#return-types-dictjson-vs-pydantic)
- [CLI Overview](#-cli-overview)
  - [CLI Cheat Sheet](#cli-cheat-sheet)
  - [CLI Examples](#cli-examples)
- [Python Usage](#-python-usage)
  - [Sync Client](#sync-client)
  - [Async Client](#async-client)
- [Contributing](#-contributing)

---

## 📦 Installation

Install from PyPI:

```bash
pip install dhis2-client
```

Or from source:

```bash
git clone https://github.com/dhis2/dhis2-python-client.git
cd dhis2-python-client
pip install -e .
```

---

## ⚙️ Configuration

### Logging

The client uses Python’s built-in logging.  
Default level = **WARNING** ⚠️. You can override via `Settings`:

```python
from dhis2_client import Settings, DHIS2Client

settings = Settings(
    base_url="http://localhost:8080",
    username="admin",
    password="district",
    log_level="DEBUG",  # INFO | WARNING | ERROR | CRITICAL
)
```

---

### Return Types (dict/JSON vs Pydantic)

By default, **methods return plain `dict` objects (JSON)** ✅  

This is controlled globally via the `Settings.return_models` flag:

- `return_models=False` (default) → always return dict/JSON unless overridden.  
- `return_models=True` → return Pydantic models by default.  

You can also override **per-call** with the `as_dict` flag.

Example:

```python
from dhis2_client import Settings, DHIS2Client

# Global default (dict/JSON)
settings = Settings(base_url="http://localhost:8080", username="admin", password="district")
client = DHIS2Client.from_settings(settings)
info = client.get_system_info()
print(info["version"])  # dict

# Global opt-in for models
settings = Settings(base_url="http://localhost:8080", username="admin", password="district", return_models=True)
client = DHIS2Client.from_settings(settings)
info_m = client.get_system_info()
print(info_m.version)  # Pydantic model

# Per-call override
info_dict = client.get_system_info(as_dict=True)     # dict
info_model = client.get_system_info(as_dict=False)   # Pydantic
```

---

## 🖥 CLI Overview

Run:

```bash
dhis2-client --help
```

Main groups:

- 🔧 **system** → system info, ping  
- 🌐 **http** → raw GET/POST/PUT/DELETE  
- 📊 **metadata** → generic CRUD for all metadata collections  
- 👤 **users** → manage users  
- 📈 **data-values** → single data value get/upsert/delete  
- 📦 **data-value-sets** → import/export entire value sets  
- 📤 **bulk** → generic bulk POST/PUT/PATCH (events, TEIs, etc.)

### CLI Cheat Sheet

| Command group     | Purpose                                      |
|-------------------|----------------------------------------------|
| 🔧 `system`       | System info, ping                            |
| 🌐 `http`         | Raw GET/POST/PUT/DELETE to any path          |
| 📊 `metadata`     | Generic CRUD for all metadata collections    |
| 👤 `users`        | Manage users (list/show/create/update/delete)|
| 📈 `data-values`  | Get/upsert/delete single data values         |
| 📦 `data-value-sets` | Import/export full sets of data values     |
| 📤 `bulk`         | Bulk JSON upload (events, TEIs, enrollments) |

All commands support:

- `--engine sync|async` (default = sync)  
- `--output table|json|yaml`  
- `--jq` for JQ filtering  
- `--password-stdin` for CI use  
- `--verbose` for detailed logging  

---

## 🚀 CLI Examples

### System info
```bash
dhis2-client system info   --base-url http://localhost:8080   --username admin --password district   --engine sync --output json
```

### Metadata
Search data elements:
```bash
dhis2-client metadata search dataElements   --base-url http://localhost:8080 --username admin --password district   --filter name:ilike:malaria --fields id --fields name --output table
```

Create from JSON:
```bash
dhis2-client metadata create organisationUnits   --base-url http://localhost:8080 --username admin --password district   --json @orgunit.json
```

### Users
```bash
dhis2-client users list   --base-url http://localhost:8080 --username admin --password district   --fields id --fields username --output table
```

### Data Values
```bash
dhis2-client data-values upsert   --de DeUid --pe 202401 --ou OuUid --value 42   --base-url http://localhost:8080 --username admin --password district
```

### Data Value Sets
Export:
```bash
dhis2-client data-value-sets export   --data-set dsUid --period 202401 --org-unit ouUid   --base-url http://localhost:8080 --username admin --password district   --dest values.json
```

Import:
```bash
dhis2-client data-value-sets import   --source @values.json   --base-url http://localhost:8080 --username admin --password district   --dry-run
```

---

## 🐍 Python Usage

### Sync Client

```python
from dhis2_client import DHIS2Client, Settings

settings = Settings(
    base_url="http://localhost:8080",
    username="admin",
    password="district",
    log_level="INFO"
)

with DHIS2Client.from_settings(settings) as client:
    # dict (default)
    info = client.get_system_info()
    print(info["version"])

    # Pydantic model
    info_m = client.get_system_info(as_dict=False)
    print(info_m.version)

    # Get organisation units
    ous = client.get_organisation_units(fields=["id","name"], as_dict=True)
    print("ou count:", len(ous))
```

---

### Async Client

```python
import asyncio
from dhis2_client import DHIS2AsyncClient, Settings

settings = Settings(
    base_url="http://localhost:8080",
    username="admin",
    password="district"
)

async def main():
    async with DHIS2AsyncClient.from_settings(settings) as client:
        # dict (default)
        info = await client.get_system_info()
        print(info["version"])

        # Pydantic model
        info_m = await client.get_system_info(as_dict=False)
        print(info_m.version)

        # Iterate org units
        async for page in client.iter_organisation_units(fields=["id","name"], as_dict=True):
            print("Page:", page)

asyncio.run(main())
```

---

## 🤝 Contributing

- Run tests with `pytest`  
- Lint with `ruff` and `black`  
- Please open issues/PRs for bugs, new CLI commands, or enhancements.  

---
