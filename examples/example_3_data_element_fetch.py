from examples._config import make_client
client = make_client()

fields='id,displayName,valueType,domainType'
filter=['name:ilike:malaria']
des = list(client.get_data_elements(fields=fields, filter=filter))
print(des)


