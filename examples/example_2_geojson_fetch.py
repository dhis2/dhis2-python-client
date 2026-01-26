import matplotlib.pyplot as plt
import geopandas as gpd
import io
import json

from examples._config import make_client
client = make_client()

info = client.get_system_info()
print('version: ', info["version"])

geojson = client.get("/api/organisationUnits.geojson", params={"level": 3})

# Convert dict -> string -> file-like object
geojson_str = json.dumps(geojson)
geojson_io = io.StringIO(geojson_str)

# Read directly into a GeoDataFrame
gdf = gpd.read_file(geojson_io)

# Show a compact summary
print(gdf[["name", "level", "geometry"]].head())

# Do a quick plot
gdf.plot(figsize=(8,8))

plt.axis('equal')
plt.tight_layout()
plt.show()