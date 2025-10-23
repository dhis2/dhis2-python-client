import matplotlib.pyplot as plt
import geopandas as gpd
import io
import json

from dhis2_client import DHIS2Client
from dhis2_client.settings import ClientSettings

# centralized config
cfg = ClientSettings(
    #base_url="https://play.im.dhis2.org/dev/",
    base_url="http://localhost:9797/",
    username="admin",
    password="district",
    log_level="INFO",        # default "WARNING"
    log_format="json",       # default "json"; use "text" for human-readable
    log_destination="stdout" # default "stderr"; can also be file path
)

client = DHIS2Client(settings=cfg)
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