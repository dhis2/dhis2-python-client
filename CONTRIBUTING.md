# 🤝 Contributing to dhis2-client

Welcome, developer! 🎉 This guide walks you through setting up, testing, building, and using **dhis2-client** locally in your projects.

---

## 📑 Table of Contents
- [🔧 Prerequisites](#-prerequisites)
- [📥 Setup](#-setup)
- [🏗️ Build & Local Deploy](#-build--local-deploy)
- [🔗 Use in Another Project](#-use-in-another-project)
- [🧪 Testing](#-testing)
- [✨ Contribution Workflow](#-contribution-workflow)
- [📚 Tips](#-tips)

---

## 🔧 Prerequisites
- Python **3.8+**
- `git`, `pip`, `venv`
- Optional: `make` for shortcuts

---

## 📥 Setup

Clone and enter the project:
```bash
git clone https://github.com/your-org/dhis2-client.git
cd dhis2-client
```

Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```bash
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 🏗️ Build & Local Deploy

### Install locally in editable mode
This lets you work on the library and use it in-place:
```bash
pip install -e .
```

### Build package artifacts
Generate **wheel** and **source distribution**:
```bash
python -m build
```

Artifacts are created in the `dist/` directory:
- `dhis2_client-x.y.z-py3-none-any.whl`
- `dhis2_client-x.y.z.tar.gz`

### Install built wheel
```bash
pip install dist/dhis2_client-x.y.z-py3-none-any.whl
```

---

## 🔗 Use in Another Project

### Editable mode (preferred for development)
From the other project’s virtualenv:
```bash
pip install -e ../dhis2-client
```

Now you can:
```python
from dhis2_client import DHIS2AsyncClient
```

Once you have built and installed ```dhis2-client``` locally (See the [Developer Onboarding Guide](DEVELOPER_GUIDE.md) for details ), you can import and use it in another project.

```python
from dhis2_client import DHIS2AsyncClient, Settings
from dhis2_client.models import DataElement, DataValue, DataValueSet
import asyncio

settings = Settings(
    base_url="https://play.dhis2.org/40.0.0",  # or your DHIS2 instance
    username="admin",
    password="district",
)

async def main():
    async with DHIS2AsyncClient.from_settings(settings) as client:

        # --- 📖 READ metadata ---
        des = await client.get_data_elements(fields=["id", "name"], page_size=5, paging=False)
        print("First 5 data elements:", [d.name for d in des])

        # --- ✨ CREATE metadata ---
        new_de = DataElement(
            name="Demo DE",
            shortName="DemoDE",
            domainType="AGGREGATE",
            valueType="NUMBER",
            aggregationType="SUM",
        )
        created = await client.post_json("/api/dataElements", new_de.model_dump())
        print("Created DataElement:", created)

        # --- 🛠️ UPDATE metadata ---
        de_id = created.get("uid") or created.get("id")
        await client.post_json(
            f"/api/dataElements/{de_id}",
            {"name": "Demo DE Updated"},
        )
        print("Updated DataElement name.")

        # --- ❌ DELETE metadata ---
        await client.delete(f"/api/dataElements/{de_id}")
        print("Deleted DataElement.")

        # --- 📊 CREATE + DELETE data values ---
        dvs = DataValueSet(
            dataSet="someDataSetId",
            period="202401",
            orgUnit="someOrgUnitId",
            dataValues=[
                DataValue(dataElement="de123456789", period="202401", orgUnit="ou123456789", value="42")
            ],
        )
        resp_create = await client.post_data_value_set(dvs, import_strategy="CREATE")
        print("DataValueSet create response:", resp_create)

        resp_delete = await client.post_data_value_set(dvs, import_strategy="DELETE")
        print("DataValueSet delete response:", resp_delete)

asyncio.run(main())

```


### Install from wheel
If you’ve built the wheel:
```bash
pip install /path/to/dhis2_client-x.y.z-py3-none-any.whl
```

---

## 🧪 Testing

Run unit tests:
```bash
pytest -q tests/unit
```

Run integration tests:
```bash
pytest -q -m integration
```

Enable write tests:
```bash
export ALLOW_DHIS2_MUTATIONS=true
pytest -q -m integration
```

Integration tests rely on `.env` with DHIS2 connection details. You can pin known dataset/orgUnit/dataElement UIDs for stability:

```env
TEST_DATASET_UID=lyLU2wR22tC
TEST_OU_UID=ImspTQPwCqd
TEST_DE_UID=fbfJHSPpUQD
```

The client auto-picks default COC/AOC.

---

## ✨ Contribution Workflow

1. **Fork** the repo
2. Create a **feature branch**
   ```bash
   git checkout -b feat/my-change
   ```
3. **Develop & test** your change
4. **Commit with style**
   ```bash
   git commit -m "feat: add paging to DataSet fetch"
   ```
5. **Push & open PR**

---

## 📚 Tips

- Use `pytest -v` for detailed test logs.
- Logging is JSON; pipe through `jq` for readability:
  ```bash
  pytest -q | jq .
  ```
- Always run `pre-commit` (if installed) before pushing:
  ```bash
  pre-commit run --all-files
  ```

---

💡 With this, you can **build, install, and use dhis2-client locally** in any project while contributing back improvements.
