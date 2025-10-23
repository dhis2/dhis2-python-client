# Import the library
from dhis2_client import DHIS2Client

# Make Auth configuratoin
client = DHIS2Client(base_url="http://localhost:9090", username="admin", password="district")

# Get current user
me = client.get_current_user(fields="id,username,firstName,surname")

payload = {}
res = client.post("/api/resourceTables/analytics", json=payload)

print('result: ', res)