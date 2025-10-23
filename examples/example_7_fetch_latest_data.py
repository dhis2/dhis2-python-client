from dhis2_client import DHIS2Client


client = DHIS2Client(base_url="http://localhost:9090", username="admin", password="district")
#FTRrcoaog83
#fbfJHSPpUQD
#Fyul5papro0
#exInDbcwJWI
data = client.analytics_latest_period_for_level('exInDbcwJWI', 2)

print('data: ', data)