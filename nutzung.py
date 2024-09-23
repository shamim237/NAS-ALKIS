import xml.etree.ElementTree as ET
import shapefile
import json
import re
import codecs
from shapely.geometry import Polygon, MultiPolygon
import sys

# Input XML file
input_xml = sys.argv[1]

# Input JSON file for bez_dict
bez_dict_file = sys.argv[2]

# Output shapefile
output_shapefile = sys.argv[3]

# Load bez_dict from JSON file
with codecs.open(bez_dict_file, 'r', encoding='utf-8') as f:
    bez_dict = json.load(f)

# Create shapefile writer
w = shapefile.Writer(output_shapefile)
w.autoBalance = 1

# Define fields for shapefile
w.field('nutzart', 'C')       # Nutzart as string
w.field('bez', 'C')           # BEZ as string
w.field('name', 'C')          # NAME as string

# Parse the XML file
tree = ET.parse(input_xml)
root = tree.getroot()

# List of tag names to process
tags_to_process = [
    "AX_Gehoelz", "AX_Wohnbauflaeche", "AX_UnlandVegetationsloseFlaeche",
    "AX_Strassenverkehr", "AX_StehendesGewaesser", "AX_SportFreizeitUndErholungsflaeche",
    "AX_Platz", "AX_Landwirtschaft", "AX_IndustrieUndGewerbeflaeche", 
    "AX_Fliessgewaesser", "AX_FlaecheGemischterNutzung", "AX_Wald", "AX_Weg", "AX_Friedhof",
    "AX_FlaecheBesondererFunktionalerPraegung", "AX_Bahnverkehr"
]

# Helper function to extract coordinates and create Polygon
def extract_polygon(coords_text):
    coords = list(map(float, coords_text.split()))
    return [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]

# Helper function to format nutzart
def format_nutzart(tag):
    # Remove 'AX_' prefix and add spaces before capital letters
    return ' '.join(re.findall('[A-Z][^A-Z]*', tag[3:]))

# Helper function to extract bez value
def extract_bez(elem):
    funktion_elem = elem.find('.//{http://www.adv-online.de/namespaces/adv/gid/6.0}funktion')
    vegetationsmerkmal_elem = elem.find('.//{http://www.adv-online.de/namespaces/adv/gid/6.0}vegetationsmerkmal')
    
    if funktion_elem is not None:
        return bez_dict.get(funktion_elem.text, "<null>")
    elif vegetationsmerkmal_elem is not None:
        return bez_dict.get(vegetationsmerkmal_elem.text, "<null>")
    else:
        return "<null>"

# Process the elements
for tag_name in tags_to_process:
    for elem in root.findall(f".//{{http://www.adv-online.de/namespaces/adv/gid/6.0}}{tag_name}"):

        # Format nutzart
        nutzart = format_nutzart(tag_name)

        # Extract bez
        bez = extract_bez(elem)

        # Extract name
        name_elem = elem.find('.//{http://www.adv-online.de/namespaces/adv/gid/6.0}name')
        name = name_elem.text if name_elem is not None else "<null>"

        # Extract coordinates for polygon
        coordinates = elem.findall('.//{http://www.opengis.net/gml/3.2}posList')
        if coordinates:
            polygon_coords = []
            for coord_elem in coordinates:
                polygon_coords.extend(extract_polygon(coord_elem.text))
            
            # Create a Shapely polygon and fix invalid geometries
            try:
                poly = Polygon(polygon_coords)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                
                if isinstance(poly, Polygon):
                    w.poly([list(poly.exterior.coords)])
                elif isinstance(poly, MultiPolygon):
                    for p in poly.geoms:
                        w.poly([list(p.exterior.coords)])
                
                # Add record to shapefile
                w.record(nutzart, bez, name)
            except Exception as e:
                print(f"Error processing polygon: {e}")

# Save shapefile
w.close()

print("Shapefile created successfully.")

# Create .prj file
prj = open(output_shapefile.replace('.shp', '.prj'), "w")
epsg = 'PROJCS["ETRS89 / UTM zone 32N",GEOGCS["ETRS89",DATUM["European_Terrestrial_Reference_System_1989",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6258"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4258"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",9],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","25832"]]'
prj.write(epsg)
prj.close()

print("Shapefile and .prj file created successfully.")