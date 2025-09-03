# 🧑‍💻 Developer Onboarding Guide

Welcome to **dhis2-client**! This guide gets you from zero → productive: environment setup, running tests (unit + live integration), code quality, and using the client from another project.

---

## 📦 Prerequisites

- **Python**: 3.8–3.12 (project CI targets 3.8 compatibility)
- **pipx** *(optional but recommended)* for developer tools  
- A DHIS2 instance for integration tests (e.g. local, test server, or `play.dhis2.org`)

> Tip: If you’re on Ubuntu, ensure `python3-venv` is installed.

---

## 🚀 Quick Start (Local Dev)

```bash
# 1) Clone and enter the repo
git clone https://github.com/dhis2/dhis2-python-client.git
cd dhis2-python-client

# 2) Create a virtualenv
python3 -m venv .venv
source .venv/bin/activate

# 3) Install dependencies
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt  # ruff, pytest, respx, etc.

# 4) Run unit tests
pytest -q tests/unit
```

---

## 🧹 Code Style & Linting

We use **Ruff** for linting/formatting (configured for a gentle, pragmatic baseline):

```bash
# See issues (won’t modify files)
ruff check .

# Auto-fix safe issues
ruff check . --fix

# Format code
ruff format .
```

**Why some N8xx / UPxxx rules are ignored?**  
We intentionally allow **mixedCase** fields in models to match DHIS2’s JSON schema (e.g., `dataElements`, `orgUnit`). This keeps request/response payloads clean and avoids ad-hoc aliasing.

> Avoid sprinkling `# noqa` unless the rule genuinely can’t be addressed. Prefer updating `ruff.toml` instead.

---

## 🧪 Tests

### Unit tests (no network)
```bash
pytest -q tests/unit
```

### Integration tests (live DHIS2)
Provide DHIS2 credentials via `.env` or environment variables:

**.env**
```ini
DHIS2_BASE_URL=https://play.dhis2.org/40.0.0
DHIS2_USERNAME=admin
DHIS2_PASSWORD=district
```

Then:

```bash
# read-only tests (safe)
pytest -q -m integration

# include mutation tests (creates/deletes metadata & data)
ALLOW_DHIS2_MUTATIONS=true pytest -q -m integration
```

**Notes:**
- Live tests gracefully skip if `.env` is missing or the server returns expected conflicts.
- Mutation tests use safe, self-contained fixtures that **create** and then **delete** test objects (DataElements, DataSets, OrgUnits) or fallback to lookup if creation fails.

---

## 🧩 Project Layout

```text
dhis2-python-client/
├─ src/
│  └─ dhis2_client/
│     ├─ __init__.py
│     ├─ client.py                # HTTP client (async), paging & convenience methods
│     ├─ exceptions.py            # Typed error mapping (HTTP → Exceptions)
│     ├─ logging_conf.py          # Structured logging primitives
│     ├─ settings.py              # Pydantic Settings (env/.env)
│     └─ models/                  # Pydantic models (request/response + periods)
│        ├─ __init__.py
│        ├─ collections.py        # Paged wrapper types
│        ├─ common.py             # IdName base type
│        ├─ data_element.py
│        ├─ data_set.py
│        ├─ data_value.py
│        ├─ data_value_set.py
│        ├─ organisation_unit.py
│        ├─ periods.py            # format/validate period strings
│        └─ system.py
├─ tests/
│  ├─ unit/
│  └─ integration/
├─ README.md
├─ CONTRIBUTING.md
├─ DEVELOPER_GUIDE.md   # ← (this file)
├─ pyproject.toml
├─ requirements.txt
├─ requirements-dev.txt
├─ .gitignore
└─ ruff.toml
```

---

## ⚙️ Settings & Auth

Settings are loaded with **Pydantic** from environment variables (or `.env`):

```python
from dhis2_client import Settings

settings = Settings(
    base_url="https://example.org",      # Required
    username="admin",                    # Basic auth (optional if using token)
    password="district",
    # token=SecretStr("..."),            # Preferred in DHIS2 2.40+ if available
    timeout=30.0,                        # seconds
    verify_ssl=True,
)
```

---

## 🌐 Using the Client

```python
import asyncio
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.models import DataElement, DataValue, DataValueSet

settings = Settings(
    base_url="https://play.dhis2.org/40.0.0",
    username="admin",
    password="district",
)

async def main():
    async with DHIS2AsyncClient.from_settings(settings) as client:
        # System info
        info = await client.get_system_info()
        print(info.version)

        # List some metadata, no paging (client flattens results)
        des = await client.get_data_elements(fields=["id","name"], page_size=5, paging=False)
        print([d.name for d in des])

        # Create + delete data values
        dvs = DataValueSet(
            dataSet="DATASET_UID",
            period="202401",
            orgUnit="ORGUNIT_UID",
            dataValues=[DataValue(dataElement="DE_UID", period="202401", orgUnit="ORGUNIT_UID", value="99")],
        )
        await client.post_data_value_set(dvs, import_strategy="CREATE")
        await client.post_data_value_set(dvs, import_strategy="DELETE")

asyncio.run(main())
```

---

## 📚 Period Formatting & Validation

```python
from datetime import date
from dhis2_client.models import format_period, validate_period

p = format_period("Monthly", date(2025, 1, 15))  # "202501"
validate_period("Weekly", "2025W03")             # ok
```

---

## 🔁 Contributing Workflow (TL;DR)

1. Branch from `main`
2. Make changes
3. Run checks: `ruff check . --fix && ruff format . && pytest -q`
4. Commit with clear message
5. Open a PR

---

## 🧪 Integration Test Details

- `tests/integration/conftest.py` contains fixtures that:
  - Read environment (.env) for credentials
  - Optionally create and link **DataSet ↔ DataElement ↔ OrgUnit** metadata
  - Use **default COC/AOC** when posting data values
  - Clean up on teardown (when mutations enabled)
- Both **safe dry-run** and **real mutation** flows are supported and guarded.

---

## 🧱 Developing Against Another Project

```bash
# In your other project's virtualenv
pip install -e /path/to/dhis2-python-client
```

Now you can:

```python
from dhis2_client import DHIS2AsyncClient, Settings
# ... use it as normal
```

---

## 🚢 Releasing (maintainers)

1. Bump version in `pyproject.toml`
2. Update `CHANGELOG.md` (if present)
3. Tag release: `git tag vX.Y.Z && git push --tags`
4. Build & publish (e.g., with `build`/`twine`) — optional, depending on release policy

---

## 🛠️ Troubleshooting

- **`respx ... not mocked`** in unit tests  
  Make sure `respx.mock(base_url="http://test")` matches the client’s base URL in the test.
- **`pre-commit >= 3.6.0` unavailable** on old Python  
  Either upgrade Python or use a lower `pre-commit` in `requirements-dev.txt`.
- **Ruff complains about mixedCase**  
  This is intentional for DHIS2 JSON parity. See `ruff.toml` ignores.

---

## 🙌 Thanks!

We love contributions — whether docs, tests, bug fixes, or new features (e.g., DHIS2 Tracker API support). See `CONTRIBUTING.md` for details and coding guidelines.
