from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings

from itertools import islice

# connection config
cfg = ClientSettings(
    base_url="https://play.im.dhis2.org/dev/",
    username="admin",
    password="district"
)
client = DHIS2Client(settings=cfg)

ous = list(client.get_organisation_units())
print("▶ Total number of ous available: ", len(ous))

print("▶ Fetching orgunits at level 3 (first 10 ous shown as sample):")
for ou in islice(client.get_organisation_units(level=3, fields="id,name", order="name:asc"), 10):
    print(f"{ou['id']} · {ou['name']}")
print("… (more not shown)")

params={
    "fields": "id,name",
    "filter": "level:eq:3"
}
raw_ous = client.get('/api/organisationUnits.json', params=params)
print('raw_ous: ', raw_ous)


#client = DHIS2Client(base_url="http://localhost:9090", token="d2p_RSY3qHZ6bCkRghud0afwMIlaTlXI2PefJLhwc2ZEaoZo1bhsFZ")

#ous = list(client.get_organisation_units())
#print("▶ Total number of ous available: ", len(ous))