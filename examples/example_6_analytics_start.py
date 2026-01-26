from examples._config import make_client
client = make_client()

# Get current user
me = client.get_current_user(fields="id,username,firstName,surname")

payload = {}
res = client.post("/api/resourceTables/analytics", json=payload)

print('result: ', res)