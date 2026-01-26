from examples._config import make_client
client = make_client()

# Get current user
me = client.get_current_user(fields="id,username,firstName,surname")

"""
    Metadata creation process:
        1. Org unit
        2. Data element
        3. Data set

    Data preparation
        1. Prepare dataValue payload
        2. Send data to DHIS2
"""

# Metadata creation #1 - create orgunit
ou = {"name": "My organisation unit", "shortName": "My org unit", "openingDate": "2020-01-01"}
ou_res = client.create_org_unit(ou)
print(f"✔ Organizational unit create status: {ou_res['status']} and UID: {ou_res['response']['uid']}")
org_unit_uid = ou_res["response"]["uid"]

# Metata creation #1 - ensure orgunit is part of user scope.
update_response = client.add_user_org_unit_scopes(me["id"],
    capture=[org_unit_uid],
    view=[org_unit_uid],
    tei=[org_unit_uid],
)
print("✔ Organisational unit scope update status:", update_response)

# Metadata creation #2 - create data element
data_element = {
    "name": "My Sample data element",
    "shortName": "Sample data element",
    "valueType": "NUMBER",
    "aggregationType": "SUM",
    "domainType": "AGGREGATE"
}
data_element_response = client.create_data_element(data_element)
print(f"✔ Data element create status: {data_element_response['status']} and UID: {data_element_response['response']['uid']}")

# Metadata creation #3 - create data set
data_set = {
    "name": "My sample data set", 
    "shortName": "Sample data set",
    "periodType": "Monthly",
    "dataSetElements": [
        {
            "dataElement": {"id": data_element_response['response']['uid']} 
        }
    ],
    "organisationUnits": [
        {
            "id": org_unit_uid 
        }
    ]
}
data_set_response = client.create_data_set(data_set)
print(f"✔ Data set create status: {data_set_response['status']} and UID: {data_set_response['response']['uid']}")

# Metadata creation #3 - ensure user has data write access to the data set
sharing = client.grant_self_data_write_on_dataset(data_set_response['response']['uid'])
print("✔ Granted myself data write on the dataset", sharing)

# Data creation #1 - create payload
client = make_client()
payload = {
    "dataValues": [
        {
            "dataElement": data_element_response['response']['uid'],
            "orgUnit": org_unit_uid,    
            "period": "202501",
            "value": '100'
        },
        {
            "dataElement": data_element_response['response']['uid'],
            "orgUnit": org_unit_uid,    
            "period": "202502",
            "value": '200'
        },
        {
            "dataElement": data_element_response['response']['uid'],
            "orgUnit": org_unit_uid,    
            "period": "202503",
            "value": '300'
        },
        {
            "dataElement": data_element_response['response']['uid'],
            "orgUnit": org_unit_uid,    
            "period": "202504",
            "value": '400'
        }
    ]
}

# Data creation #2 - post payload
res = client.post("/api/dataValueSets", json=payload)
print("✔ Data value set post status: ", res['httpStatusCode'])


