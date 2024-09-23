import geopandas as gpd
from shapely.ops import unary_union
import shapefile
from shapely.geometry import Polygon, MultiPolygon
import sys

# Input shapefile
input_shapefile = sys.argv[1]

# Output shapefile
output_shapefile = sys.argv[2]

# Step 1: Load the shapefile
gdf = gpd.read_file(input_shapefile)

# Step 2: Fix invalid geometries
gdf['geometry'] = gdf['geometry'].buffer(0)

# Step 3: Group by gemarkung and create exterior boundaries
gemarkung_boundaries = {}
gemarkung_data = {}
for gemarkung, group in gdf.groupby('gemarkung'):
    merged_polygon = unary_union(group.geometry)
    if isinstance(merged_polygon, Polygon):
        exterior_boundary = Polygon(merged_polygon.exterior)
    elif isinstance(merged_polygon, MultiPolygon):
        exterior_boundary = MultiPolygon([Polygon(poly.exterior) for poly in merged_polygon.geoms])
    else:
        print(f"Skipping invalid geometry for gemarkung: {gemarkung}")
        continue
    gemarkung_boundaries[gemarkung] = exterior_boundary
    
    # Store additional data for each gemarkung
    sample_row = group.iloc[0]
    gemarkung_data[gemarkung] = {
        'gemeinde': sample_row['gemeinde'],
        'schluessel': sample_row['flstkennz'].split('___')[0]
    }

# Step 4: Create a new shapefile with the exterior boundaries
w = shapefile.Writer(output_shapefile)
w.autoBalance = 1

# Define fields for shapefile
w.field('oid_1', 'C')
w.field('art', 'C')
w.field('name', 'C')
w.field('schluessel', 'C')
w.field('gemeinde', 'C')

# Add geometries and attribute values to the shapefile
for gemarkung, boundary in gemarkung_boundaries.items():
    data = gemarkung_data[gemarkung]
    
    # Original record
    if isinstance(boundary, Polygon):
        w.poly([list(boundary.exterior.coords)])
        w.record(f"DE{data['schluessel']}", 'Gemarkung', gemarkung, data['schluessel'], data['gemeinde'])
    elif isinstance(boundary, MultiPolygon):
        for poly in boundary.geoms:
            w.poly([list(poly.exterior.coords)])
            w.record(f"DE{data['schluessel']}", 'Gemarkung', gemarkung, data['schluessel'], data['gemeinde'])
    
    # Additional record
    if isinstance(boundary, Polygon):
        w.poly([list(boundary.exterior.coords)])
        w.record(f"DE{data['schluessel']}000", 'Gemarkungsteil / Flur', 'Flur', f"{data['schluessel']}00", data['gemeinde'])
    elif isinstance(boundary, MultiPolygon):
        for poly in boundary.geoms:
            w.poly([list(poly.exterior.coords)])
            w.record(f"DE{data['schluessel']}000", 'Gemarkungsteil / Flur', 'Flur', f"{data['schluessel']}00", data['gemeinde'])

# Define spatial reference (projection file)
with open(output_shapefile.replace('.shp', '.prj'), 'w') as prj_file:
    prj_file.write('PROJCS["ETRS89 / UTM zone 32N",'
                   'GEOGCS["ETRS89",'
                   'DATUM["European_Terrestrial_Reference_System_1989",'
                   'SPHEROID["GRS 1980",6378137,298.257222101]],'
                   'PRIMEM["Greenwich",0],'
                   'UNIT["degree",0.0174532925199433]],'
                   'PROJECTION["Transverse_Mercator"],'
                   'PARAMETER["latitude_of_origin",0],'
                   'PARAMETER["central_meridian",9],'
                   'PARAMETER["scale_factor",0.9996],'
                   'PARAMETER["false_easting",500000],'
                   'PARAMETER["false_northing",0],'
                   'UNIT["metre",1]]')

# Save the shapefile
w.close()

print(f"Shapefile '{output_shapefile}' created successfully with exterior boundaries and additional fields.")