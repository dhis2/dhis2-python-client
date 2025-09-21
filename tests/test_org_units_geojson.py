import httpx
import pytest

from dhis2_client import DHIS2Client

BASE = "http://test"


@pytest.mark.unit
def test_get_organisation_units_geojson(respx_mock):
    # Minimal valid GeoJSON FeatureCollection
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                "properties": {"id": "ou1", "displayName": "Root OU"},
            }
        ],
    }
    respx_mock.get(f"{BASE}/api/organisationUnits.geojson").mock(
        return_value=httpx.Response(200, json=payload)
    )

    c = DHIS2Client(BASE)
    got = c.get_organisation_units_geojson(level=2, fields="id,displayName,geometry")

    assert got["type"] == "FeatureCollection"
    assert got["features"][0]["properties"]["id"] == "ou1"

    # Ensure key query params flowed through (no paging here)
    req = respx_mock.calls[-1].request
    qs = dict(httpx.QueryParams(req.url.query))
    assert qs == {"level": "2", "fields": "id,displayName,geometry"}


@pytest.mark.unit
def test_get_org_unit_geojson_single(respx_mock):
    # Some servers return Feature, others a one-item FeatureCollection.
    # We'll mock a single Feature to keep the test deterministic.
    payload = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [10.1, 59.9]},
        "properties": {"id": "ouX", "displayName": "Oslo Clinic"},
    }
    respx_mock.get(f"{BASE}/api/organisationUnits/ouX.geojson").mock(
        return_value=httpx.Response(200, json=payload)
    )

    c = DHIS2Client(BASE)
    got = c.get_org_unit_geojson("ouX", fields="id,displayName,geometry")

    assert got["type"] == "Feature"
    assert got["properties"]["id"] == "ouX"

    req = respx_mock.calls[-1].request
    qs = dict(httpx.QueryParams(req.url.query))
    assert qs == {"fields": "id,displayName,geometry"}
