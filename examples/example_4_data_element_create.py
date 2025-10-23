from dhis2_client import DHIS2Client

client = DHIS2Client(base_url="http://localhost:9292", username="admin", password="district")

# Metadata creation - create data elements
data_elements = [
    {
        "id": "xox6CYtTI46",
        "name": "Air temperature (ERA5-Land)_1",
        "shortName": "Air temperature 1",
        "code": "ERA5_LAND_TEMPERATURE_1",
        "description": "Average air temperature in °C at 2 m above the surface. Data source: ERA5-Land / Copernicus Climate Change Service",
        "valueType": "NUMBER",
        "aggregationType": "SUM",
        "domainType": "AGGREGATE",
        "zeroIsSignificant": True
    },
    {
        "id": "KUq5Ul3LGPE",
        "name": "Max air temperature (ERA5-Land)_1",
        "shortName": "Max air temperature_1",
        "code": "ERA5_LAND_TEMPERATURE_MAX_1",
        "description": "Maximum air temperature in °C at 2 m above the surface. Data source: ERA5-Land / Copernicus Climate Change Service",
        "valueType": "NUMBER",
        "aggregationType": "MAX",
        "domainType": "AGGREGATE",
        "zeroIsSignificant": True
    }
]

resp = client.post(
    "/api/metadata",
    json={"dataElements": data_elements},
    params={
        "importStrategy": "CREATE_AND_UPDATE",    # or CREATE_AND_UPDATE
        "atomicMode": "NONE",          # or ALL (all-or-nothing)
        "async": "false",              # keep sync
        "dryRun": "false",             # set true to validate first
    },
)
print(resp)  # DHIS2 metadata import report