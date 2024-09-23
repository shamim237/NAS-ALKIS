import xml.etree.ElementTree as ET
import shapefile
import sys

# Input XML file
input_xml = sys.argv[1]

# Output shapefile
output_shapefile = sys.argv[2]

# Create shapefile writer
w = shapefile.Writer(output_shapefile)
w.autoBalance = 1

# Define fields for shapefile
w.field('gebnutzbez', 'C')      # Gebaeude Nutzung Bezeichnung
w.field('funktion', 'C')        # Funktion value (mapped to text)
w.field('fktkurz', 'C')         # Kurz Funktion (<null>)
w.field('name', 'C')            # Name value
w.field('anzahlgs', 'C')        # Anzahl der Oberirdischen Geschosse
w.field('lagebeztxt', 'C')      # Lagebezeichnung text

# Parse the XML file
tree = ET.parse(input_xml)
root = tree.getroot()

# Namespace map
ns = {'gml': 'http://www.opengis.net/gml/3.2',
      'adv': 'http://www.adv-online.de/namespaces/adv/gid/6.0'}

# Building function mapping
funktion_mapping = {
    '1000': 'Wohngebäude',
    '2000': 'Gebäude für Wirtschaft oder Gewerbe',
    '3000': 'Gebäude für öffentliche Zwecke',
    '3020': 'Gebäude für Bildung und Forschung',
    '2463': 'Garage',
    '1610': 'Überdachung',
    '2523': 'Umformer',
    '1620': 'Treppe',
    '9999': 'Sonstiges',
    '1700': 'Mauer',
    '3041': 'Kirche',
    '3065': 'Kinderkrippe, Kindergarten, Kindertagesstätte',
    '3043': 'Kapelle',
    '3072': 'Feuerwehr'
}

# Helper function to extract polygon coordinates
def extract_polygon(coords_text):
    try:
        coords = list(map(float, coords_text.split()))
        return [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
    except Exception as e:
        print(f"Error parsing coordinates: {e}")
        return None

# Cache frequently accessed elements
lagebezeichnung_cache = {}
for lage_elem in root.findall('.//adv:AX_LagebezeichnungMitHausnummer', ns):
    gml_id = lage_elem.attrib.get('{http://www.opengis.net/gml/3.2}id')
    if gml_id:
        unverschluesselt_elem = lage_elem.find('.//adv:lagebezeichnung/adv:AX_Lagebezeichnung/adv:unverschluesselt', ns)
        hausnummer_elem = lage_elem.find('.//adv:hausnummer', ns)
        unverschluesselt = unverschluesselt_elem.text if unverschluesselt_elem is not None else ''
        hausnummer = hausnummer_elem.text if hausnummer_elem is not None else ''
        lagebezeichnung_cache[gml_id] = f"{unverschluesselt} {hausnummer}".strip()

# Process AX_Gebaeude and AX_SonstigesBauwerkOderSonstigeEinrichtung
for gebaeude in root.findall('.//adv:AX_Gebaeude', ns) + root.findall('.//adv:AX_SonstigesBauwerkOderSonstigeEinrichtung', ns):
    # Create 'gebnutzbez' value
    gebnutzbez = 'Gebaeude' if gebaeude.tag == '{http://www.adv-online.de/namespaces/adv/gid/6.0}AX_Gebaeude' else 'Sonstiges Bauwerk Oder Sonstige Einrichtung'

    # Extract and map 'funktion' value
    funktion_elem = gebaeude.find('.//adv:gebaeudefunktion', ns)
    if funktion_elem is None:
        funktion_elem = gebaeude.find('.//adv:bauwerksfunktion', ns)
    funktion = funktion_mapping.get(funktion_elem.text, 'Unbekannt') if funktion_elem is not None and funktion_elem.text else '<null>'

    # Set 'fktkurz' to '<null>'
    fktkurz = '<null>'

    # Extract 'name' value
    name_elem = gebaeude.find('.//adv:name', ns)
    name = name_elem.text if name_elem is not None else '<null>'

    # Extract 'anzahlDerOberirdischenGeschosse' value
    anzahlgs_elem = gebaeude.find('.//adv:anzahlDerOberirdischenGeschosse', ns)
    anzahlgs = anzahlgs_elem.text if anzahlgs_elem is not None else '<null>'

    # Extract 'lagebeztxt' based on the 'zeigtAuf' reference
    zeigtauf_elem = gebaeude.find('.//adv:zeigtAuf', ns)
    lagebeztxt = '<null>'
    if zeigtauf_elem is not None:
        xlink_href = zeigtauf_elem.attrib.get('{http://www.w3.org/1999/xlink}href')
        if xlink_href:
            gml_id = xlink_href.split(':')[-1]
            lagebeztxt = lagebezeichnung_cache.get(gml_id, '<null>')

    # Extract coordinates for the polygon
    pos_list = gebaeude.findall('.//gml:posList', ns)
    polygon_coords = []
    if pos_list:
        for pos in pos_list:
            coords = extract_polygon(pos.text)
            if coords:
                polygon_coords.extend(coords)

    if polygon_coords:
        # Add polygon and record to shapefile
        w.poly([polygon_coords])
        w.record(gebnutzbez, funktion, fktkurz, name, anzahlgs, lagebeztxt)

# Save shapefile
w.close()

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