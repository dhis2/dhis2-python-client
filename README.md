# dhis2-client

> Simple, synchronous DHIS2 Web API client — **dict/JSON only**, Jupyter-friendly (no context managers), **clean paging**, **read-only users**, CRUD for metadata (org units, data elements, data sets), **data values** & **data value sets**, **analytics**, and **minimal logging** by default.

---

## Table of Contents
- [dhis2-client](#dhis2-client)
  - [Table of Contents](#table-of-contents)
  - [Why this client?](#why-this-client)
  - [Installation](#installation)
  - [Requirements](#requirements)
  - [Quickstart](#quickstart)
  - [Authentication \& Settings](#authentication--settings)
  - [Logging](#logging)
  - [Paging](#paging)
  - [Collections: page-by-page iteration](#collections-page-by-page-iteration)
    - [Examples](#examples)
  - [Sharing](#sharing)
    - [Examples](#examples-1)
  - [User OrgUnit Scope](#user-orgunit-scope)
    - [Examples](#examples-2)
  - [Convenience Methods](#convenience-methods)
    - [Core (raw API calls)](#core-raw-api-calls)
    - [System](#system)
    - [Users (read-only)](#users-read-only)
    - [Organisation Units](#organisation-units)
      - [GeoJSON](#geojson)
    - [Data Elements](#data-elements)
    - [Data Sets](#data-sets)
    - [Data Values](#data-values)
    - [Data Value Sets](#data-value-sets)
    - [Analytics](#analytics)
  - [Examples](#examples-3)
    - [Users (read-only)](#users-read-only-1)
    - [Organisation Units](#organisation-units-1)
      - [GeoJSON](#geojson-1)
    - [Data Elements](#data-elements-1)
    - [Data Sets](#data-sets-1)
    - [Data Values](#data-values-1)
    - [Data Value Sets](#data-value-sets-1)
    - [Analytics](#analytics-1)
  - [Raw API calls](#raw-api-calls)
  - [Testing](#testing)
  - [Dev Setup](#dev-setup)
  - [Integration Tests](#integration-tests)
  - [Roadmap](#roadmap)
  - [License](#license)

---

## Why this client?

DHIS2 is one of the most widely used health information platforms worldwide, and Python is a popular choice in data science, research, and integration workflows. Bringing the two together makes it easier to build analytics, integrations, and automation around DHIS2 data.

This client provides a **lightweight and simple** way to work with the DHIS2 Web API:

- Always returns plain Python `dict` / JSON objects — no custom models or ORM layers.  
- Handles **paging** cleanly, so you can iterate over large DHIS2 collections without surprises.  
- Offers **convenience methods** for common entities (users, organisation units, data elements, data sets, data values, analytics) while keeping full access to the raw API.  
- Keeps setup minimal — synchronous, Jupyter-friendly, and easy to configure.  

---

## Installation

> Requires **Python 3.10+**

At this stage the package is not yet published on PyPI.  
You can install it from source:

```bash
# Clone the repo
git clone https://github.com/dhis2/dhis2-python-client.git
cd dhis2-python-client

# Install in editable/development mode
pip install -e .
```

---

## Requirements

- Python **3.10+**
- DHIS2 server URL and valid credentials (Basic or token)

---

## Quickstart

```python
from dhis2_client import DHIS2Client

client = DHIS2Client(
    base_url="http://localhost:8080",
    username="admin",
    password="district",  # Basic auth by default
)

# Iterate users (read-only)
for u in client.get_users(fields="id,username", order="username:asc"):
    print(u)

# Fetch all data elements into a list (respecting paging)
all_des = client.fetch_all("/api/dataElements", params={"fields": "id,displayName"})
```
---

## Authentication & Settings

You can configure the client directly with kwargs or centrally with a ClientSettings object.

```python
from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings

# Recommended: central settings
cfg = ClientSettings(
    base_url="http://localhost:8080",
    username="admin",
    password="district",
    log_level="INFO",        # default "WARNING"
    log_format="json",       # default "json"; use "text" for human-readable
    log_destination="stdout" # default "stderr"; can also be file path
)

client = DHIS2Client(settings=cfg)
info = client.get_system_info()
print(info["version"])
```
Kwargs override settings if both are provided:
```python
client = DHIS2Client(settings=cfg, log_level="DEBUG")  # DEBUG takes precedence

```
---

## Logging

- **Default**: JSON logs at WARNING level to stderr.
- **Configurable**: via ClientSettings or constructor kwargs.

```python
# JSON (default) logs at INFO to stdout
cfg = ClientSettings(
  base_url="http://localhost:8080", 
  username="admin", 
  password="district", 
  log_level="INFO", log_destination="stdout")
client = DHIS2Client(settings=cfg)

# Human-readable text logs
client = DHIS2Client(
  "http://localhost:8080",
  username="admin", 
  password="district",
  log_level="INFO", log_format="text")

# File logging
client = DHIS2Client("http://localhost:8080",
                     username="admin", password="district",
                     log_level="DEBUG", log_destination="/tmp/dhis2_client.log")

```

Example output:
```json
{"ts":"2025-09-19T14:20:01+0000","level":"INFO","logger":"dhis2_client","message":"Request GET /api/system/info params=None"}
```

---

## Paging

- Default `pageSize=50`.
- `get_*s()` yield **items** across pages.
- `fetch_all()` returns a **list** of all items.

```python
for ou in client.get_organisation_units(level=2, fields="id,displayName"):
    ...
```
---

## Collections: page-by-page iteration

All collection convenience methods (`get_data_elements`, `get_users`, `get_organisation_units`, `get_data_sets`, …) fetch results **page by page** from DHIS2 until all matching items are returned.  

- ✅ Safe for large DHIS2 servers (does not load everything in one huge response).
- ✅ Transparent pass-through: you control `page`, `pageSize`, `filter`, `fields`, etc.
- ❌ These methods do **not** include the `pager` block that DHIS2 returns. Use `client.get(...)` directly if you need that metadata.

### Examples

Iterate over all matching data elements (fetches pages of 50 by default):

```python
for de in client.get_data_elements(fields="id,displayName"):
    print(de["id"], de["displayName"])
```

Materialize in memory (not recommended for huge datasets):

```python
des = list(client.get_data_elements(fields="id,displayName"))
print(len(des))  # total number of matching items across all pages
```

Get paging info (total, page count, etc.) directly from DHIS2:

```python
raw = client.get("/api/dataElements", params={"page": 1, "pageSize": 50})
print(raw["pager"]["total"])
```

---

## Sharing

This client mirrors DHIS2’s common default posture where **Public access** is
“Can edit and view metadata” (metadata read+write). Access masks:

- `DATA_READ`  = `rwr-----`   (metadata rw, data r)
- `DATA_WRITE` = `rwrw----`   (metadata rw, data rw — typical for capture)
- `META_READ`  = `rw-------`  (metadata rw, no data)
- `META_WRITE` = `rw-------`  (same string, alias for clarity)
- `NO_ACCESS`  = `--------`   (deny all)

### Examples

```python
# Grant *yourself* data write (plus metadata rw baseline) on a Program
client.grant_self_access(object_type="program", object_id="PrA123", access=DATA_WRITE)  # "rwrw----"

# Change only public access → set to metadata rw (rw-------)
client.set_public_access(object_type="dashboard", object_id="db789", public_access=META_WRITE)

# Grant user data set write access
client.set_dataset_data_write("Ds1", user_ids=["u1"], user_group_ids=["gEditors"])

# Stricter security: remove all public access
client.set_dataset_data_write("Ds2", public_access=NO_ACCESS)  # "--------"
```

---

## User OrgUnit Scope

Methods are operation-specific; kwargs are just the **scopes**:

- `capture` → `/organisationUnits`
- `view`    → `/dataViewOrganisationUnits`
- `tei`     → `/teiSearchOrganisationUnits`

### Examples

```python
# Current user
client.add_my_org_unit_scopes(capture=["ouCapA", "ouCapB"], view=["ouViewX"])      # append (dedupes)
client.replace_my_org_unit_scopes(tei=["ouSearch1", "ouSearch2"])                  # set exactly
client.remove_my_org_unit_scopes(capture=["ouCapB"], tei=["ouSearch2"])            # remove by ID

# Another user (UID)
uid = "u123456"
client.add_user_org_unit_scopes(uid, capture=["ouA"], view=["ouB"])
client.replace_user_org_unit_scopes(uid, capture=["ouOnly"])
client.remove_user_org_unit_scopes(uid, tei=["ouOldSearch"])
```
---

## Convenience Methods

### Core (raw API calls)
```
get(path, params=None) -> dict
post(path, json=None) -> dict
put(path, json=None) -> dict
delete(path, params=None) -> dict
list_paged(path, params=None, page_size=None, item_key=None) -> Iterable[dict]
fetch_all(path, params=None, item_key=None) -> list[dict]
```

### System
```
get_system_info() -> dict
```

### Users (read-only)
```
get_users(**filters) -> Iterable[dict]
get_user(uid, *, fields=None) -> dict
```

### Organisation Units
```
get_organisation_units(**filters) -> Iterable[dict]
get_org_unit(uid, *, fields=None) -> dict
create_org_unit(payload) -> dict
update_org_unit(uid, payload) -> dict
delete_org_unit(uid) -> dict
get_org_unit_tree(root_uid=None, levels=None) -> dict
```

#### GeoJSON

```python
get_organisation_units_geojson(**params) -> dict
get_org_unit_geojson(uid, **params) -> dict
```

### Data Elements
```
get_data_elements(**filters) -> Iterable[dict]
get_data_element(uid, *, fields=None) -> dict
create_data_element(payload) -> dict
update_data_element(uid, payload) -> dict
delete_data_element(uid) -> dict
```

### Data Sets
```
get_data_sets(**filters) -> Iterable[dict]
get_data_set(uid, *, fields=None) -> dict
create_data_set(payload) -> dict
update_data_set(uid, payload) -> dict
delete_data_set(uid) -> dict
```

### Data Values
```
get_data_value(de, pe, ou, co=None, aoc=None, cc=None, cp=None) -> dict
set_data_value(de, pe, ou, value, **kwargs) -> dict
delete_data_value(de, pe, ou, **kwargs) -> dict
```

### Data Value Sets
```
get_data_value_set(params: dict) -> dict
post_data_value_set(payload: dict) -> dict
```

### Analytics
```
get_analytics(table: str = "analytics", **params) -> dict
```

---

## Examples

### Users (read-only)

```python
# List users
for u in client.get_users(fields="id,username", order="username:asc"):
    print(u)

# Single user
user = client.get_user("u123", fields="id,username,displayName")
```

### Organisation Units

```python
# Iterate OU level 2
for ou in client.get_organisation_units(level=2, fields="id,displayName"):
    print(ou)

# Single OU
ou = client.get_org_unit("ou123", fields="id,displayName")

# Create/Update/Delete OU
client.create_org_unit({"name": "Clinic A", "shortName": "ClinicA", "openingDate": "2020-01-01"})
client.update_org_unit("ou123", {"name": "Clinic Alpha"})
client.delete_org_unit("ou123")

# Tree
tree = client.get_org_unit_tree(root_uid="ouROOT")
```

#### GeoJSON

```python
# Collection as GeoJSON (unpaged FeatureCollection)
fc = client.get_organisation_units_geojson(level=2, fields="id,displayName,geometry")

# Single org unit as GeoJSON
feat = client.get_org_unit_geojson("ou123", fields="id,displayName,geometry")
```

### Data Elements

```python
# List
for de in client.get_data_elements(fields="id,displayName", filter=["valueType:eq:INTEGER"]):
    print(de)

# CRUD
client.create_data_element({"name": "New DE", "shortName": "NDE", "valueType": "NUMBER"})
de = client.get_data_element("de123", fields="id,displayName,valueType")
client.update_data_element("de123", {"valueType": "INTEGER"})
client.delete_data_element("de123")
```

### Data Sets

```python
for ds in client.get_data_sets(fields="id,displayName"):
    print(ds)

ds = client.get_data_set("ds123", fields="id,displayName")
client.create_data_set({"name": "My DS", "periodType": "Monthly"})
client.update_data_set("ds123", {"name": "My DS (Updated)"})
client.delete_data_set("ds123")
```

### Data Values

```python
# Single data value lifecycle
client.set_data_value(de="de1", pe="202401", ou="ou1", value="42")
val = client.get_data_value(de="de1", pe="202401", ou="ou1")
client.delete_data_value(de="de1", pe="202401", ou="ou1")
```

### Data Value Sets

```python
# Pull a batch
dvs = client.get_data_value_set({"dataSet": "ds1", "period": "202401", "orgUnit": "ou1"})

# Push a batch
client.post_data_value_set({
  "dataSet": "ds1",
  "orgUnit": "ou1",
  "period": "202401",
  "dataValues": [
    {"dataElement": "de1", "categoryOptionCombo": "co1", "value": "5"},
    {"dataElement": "de2", "categoryOptionCombo": "co1", "value": "9"}
  ]
})
```

### Analytics

```python
pivot = client.get_analytics(
  dimension=["dx:de1;de2", "pe:LAST_12_MONTHS", "ou:LEVEL-2"],
  displayProperty="NAME",
  skipMeta=True,
)
```

---

## Raw API calls

Not every DHIS2 endpoint has a convenience wrapper yet. You can always use the **core methods** to call any path directly:

```python
# Arbitrary GET
resp = client.get("/api/indicators", params={"fields": "id,displayName"})

# Single item
indicator = client.get("/api/indicators/abc123", params={"fields": "id,displayName"})

# Create
ou = client.post("/api/organisationUnits", json={
    "name": "Clinic A",
    "shortName": "ClinicA",
    "openingDate": "2020-01-01"
})

# Update
client.put("/api/dataElements/de123", json={"valueType": "INTEGER"})

# Delete
client.delete("/api/dataSets/ds123")

# Iterate paged collection
for de in client.list_paged(
    "/api/dataElements",
    params={"fields": "id,displayName"},
    item_key="dataElements"
):
    print(de)
```

---

## Testing

- Run **unit tests** (mocked; no .env needed):

```bash
pytest -q
```

- Lint/format:

```bash
ruff check .
ruff format .
```

---

## Dev Setup

```bash
pip install -r requirements-dev.txt
```

Includes: `pytest`, `ruff`, `respx`, `python-dotenv`.

---

## Integration Tests

Read-only integration tests (if you have credentials):

```bash
export DHIS2_BASE_URL="http://localhost:8080"
export DHIS2_USERNAME="admin"
export DHIS2_PASSWORD="district"
pytest -m integration -q
```

Destructive tests (opt-in; **be careful**):

```bash
export DHIS2_ALLOW_MUTATIONS=true
pytest -m integration -q tests/integration/test_live_mutations.py
```

---

## Roadmap

- Stabilize core API and paging
- Optional async & CLI (later)
- More helpers (e.g., file resources, indicators)

---

## License

BSD-3-Clause
