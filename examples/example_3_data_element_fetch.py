from dhis2_client import DHIS2Client

client = DHIS2Client(base_url="http://localhost:9797", username="admin", password="district")

fields='id,displayName,valueType,domainType'
filter=['name:ilike:malaria']
des = list(client.get_data_elements(fields=fields, filter=filter))
print(des)


