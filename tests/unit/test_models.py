from dhis2_client.models import DataElement, DataValue, DataValueSet, OrganisationUnits


def test_collection_parsing():
    payload = {"organisationUnits": [{"id": "A", "name": "HQ"}], "pager": {"page": 1}}
    parsed = OrganisationUnits.model_validate(payload)
    assert parsed.organisationUnits[0].name == "HQ"


def test_request_models_forbid_extras():
    dvs = DataValueSet(
        dataSet="abc",
        period="202401",
        orgUnit="ou1",
        dataValues=[DataValue(dataElement="de1", period="202401", orgUnit="ou1", value="10")],
    )
    dumped = dvs.model_dump()
    assert "dataValues" in dumped


def test_data_element_response_allows_unknown():
    de = DataElement.model_validate({"id": "de1", "name": "Demo", "unknownField": "ignored"})
    assert de.id == "de1"
