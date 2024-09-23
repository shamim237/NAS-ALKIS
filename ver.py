import geopandas as gpd
from shapely.ops import unary_union
import xml.etree.ElementTree as ET
import shapefile
from shapely.geometry import Polygon, MultiPolygon
import sys

# Input shapefile
input_shapefile = sys.argv[1]

# Input XML file
input_xml = sys.argv[2]

# Output shapefile
output_shapefile = sys.argv[3]

# Create shapefile writer for the output
w = shapefile.Writer(output_shapefile)
w.autoBalance = 1

# Step 1: Load the shapefile and get the merged polygon with exterior boundary
gdf = gpd.read_file(input_shapefile)

# Step 1.1: Identify and fix invalid geometries
gdf['valid'] = gdf.is_valid

# Print invalid geometries
invalid_geometries = gdf[~gdf['valid']]
if not invalid_geometries.empty:
    print(f"Invalid geometries found: {len(invalid_geometries)}. Attempting to fix them.")

# Fix invalid geometries using buffer(0)
gdf['geometry'] = gdf['geometry'].buffer(0)

# Combine all polygons into one using unary_union
merged_polygon = unary_union(gdf.geometry)

# Step 1.2: Check if merged_polygon is a MultiPolygon or a single Polygon
if isinstance(merged_polygon, Polygon):
    exterior_boundaries = [merged_polygon.exterior]
elif isinstance(merged_polygon, MultiPolygon):
    exterior_boundaries = [poly.exterior for poly in merged_polygon.geoms]
else:
    raise TypeError("Resulting geometry is neither a Polygon nor a MultiPolygon.")

# Define fields for shapefile
w.field('art', 'C')          # Type of tag (Gemeinde, Bundesland, etc.)
w.field('name', 'C')         # Name value
w.field('schluessel', 'C')   # Schlüssel value
w.field('uebaname', 'C')     # Uebaname value
w.field('ueobjekt', 'C')     # Ueobjekt value

# Parse the XML file
tree = ET.parse(input_xml)
root = tree.getroot()

# Namespace map
ns = {'gml': 'http://www.opengis.net/gml/3.2',
      'adv': 'http://www.adv-online.de/namespaces/adv/gid/6.0'}

# Store the tag names
tag_names = {
    'AX_Gemeinde': 'Gemeinde',
    'AX_Bundesland': 'Bundesland',
    'AX_Regierungsbezirk': 'Regierungsbezirk',
    'AX_KreisRegion': 'Kreis / kreisfreie Stadt'
}

# Track if "Gemeinde" and "Kreis / kreisfreie Stadt" have already been added
first_gemeinde_added = False
first_kreis_added = False

# Helper function to extract polygon coordinates
def extract_polygon(coords_text):
    try:
        coords = list(map(float, coords_text.split()))
        return [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
    except Exception as e:
        print(f"Error parsing coordinates: {e}")
        return None

# Step 3: Add the extracted XML data to the shapefile along with the exterior boundary from the polygon
tags = ['AX_Gemeinde', 'AX_Bundesland', 'AX_Regierungsbezirk', 'AX_KreisRegion']
data = {}

for tag in tags:
    for element in root.findall(f'.//adv:{tag}', ns):
        tag_name = tag_names.get(tag, '<null>')
        name_elem = element.find('.//adv:bezeichnung', ns)
        name = name_elem.text if name_elem is not None else '<null>'
        
        schluessel_elem = element.find('.//adv:schluesselGesamt', ns)
        schluessel = schluessel_elem.text if schluessel_elem is not None else '<null>'
        
        # Define uebaname based on tag
        if tag == 'AX_Gemeinde':
            uebaname = data.get('AX_KreisRegion', {}).get('name', '<null>')
        elif tag == 'AX_Bundesland':
            uebaname = '<null>'
        elif tag == 'AX_Regierungsbezirk':
            uebaname = data.get('AX_Bundesland', {}).get('name', '<null>')
        elif tag == 'AX_KreisRegion':
            uebaname = data.get('AX_Regierungsbezirk', {}).get('name', '<null>')
        
        # Define ueobjekt based on schluessel
        if tag == 'AX_Gemeinde':
            ueobjekt = f"DE{schluessel[:5]}"
        elif tag == 'AX_Bundesland':
            ueobjekt = '<null>'
        elif tag == 'AX_Regierungsbezirk':
            ueobjekt = '<null>'
        elif tag == 'AX_KreisRegion':
            ueobjekt = f"DE{schluessel[:3]}"
        
        data[tag] = {'name': name, 'schluessel': schluessel}
        
        # Skip if first Gemeinde or Kreis / kreisfreie Stadt has already been added
        if (tag == 'AX_Gemeinde' and first_gemeinde_added) or (tag == 'AX_KreisRegion' and first_kreis_added):
            continue

        # Set flags after first Gemeinde or Kreis / kreisfreie Stadt is added
        if tag == 'AX_Gemeinde':
            first_gemeinde_added = True
        elif tag == 'AX_KreisRegion':
            first_kreis_added = True

        print("="*50)
        print(tag_name)
        print(name)
        print(schluessel)
        print(uebaname)
        print(ueobjekt)
        print("="*50)
        
        # Add record to shapefile (with the tag data)
        w.record(tag_name, name, schluessel, uebaname, ueobjekt)

# Step 4: Add the exterior boundaries to the shapefile
for boundary in exterior_boundaries:
    w.poly([list(boundary.coords)])

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