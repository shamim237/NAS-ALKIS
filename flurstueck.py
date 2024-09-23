import time
import geopandas as gpd
from shapely.geometry import Polygon
import xml.etree.ElementTree as ET
import multiprocessing as mp
import sys

# Parse the XML file correctly
def parse_xml(file_path):
    tree = ET.parse(file_path)  # Parse the entire XML file
    root = tree.getroot()       # Get the root element
    return root

# Extract coordinates in bulk
def extract_coordinates(posList):
    coordinates = [float(x) for x in posList.strip().split()]
    return [(coordinates[i], coordinates[i + 1]) for i in range(0, len(coordinates), 2)]

# Create flurstnr based on zaehler and nenner
def create_flurstnr(zaehler, nenner=None):
    return f"{zaehler}/{nenner}" if nenner else zaehler

# Create gmdschl by merging land, kreis, regierungsbezirk, and gemeinde
def create_gmdschl(land, regierungsbezirk, kreis, gemeinde):
    return f"{land}{regierungsbezirk}{kreis}{gemeinde}"

# Find and extract kreis values
def find_kreis(root, namespaces):
    kreis_dict = {}
    for kreis_region in root.findall('.//adv:AX_KreisRegion', namespaces):
        schluessel_gesamt = kreis_region.find('.//adv:schluesselGesamt', namespaces)
        if schluessel_gesamt is not None:
            kreis_dict[schluessel_gesamt.text] = kreis_region.find('.//adv:bezeichnung', namespaces).text
    return kreis_dict

# Find and extract regbezirk values
def find_regbezirk(root, namespaces):
    regbezirk_dict = {}
    for regbezirk in root.findall('.//adv:AX_Regierungsbezirk', namespaces):
        schluessel_gesamt = regbezirk.find('.//adv:schluesselGesamt', namespaces)
        bezeichnung = regbezirk.find('.//adv:bezeichnung', namespaces)
        if schluessel_gesamt is not None and bezeichnung is not None:
            regbezirk_dict[schluessel_gesamt.text] = bezeichnung.text
    return regbezirk_dict

# Create lookup dictionary
def create_lookup_dict(root, tag, key_path, value_path, namespaces):
    lookup_dict = {}
    for element in root.findall(f'.//adv:{tag}', namespaces):
        key = element.find(key_path, namespaces)
        value = element.find(value_path, namespaces)
        if key is not None and value is not None:
            lookup_dict[key.text] = value.text
    return lookup_dict

# Create lagebeztxt lookup dictionary
def create_lagebeztxt_dict(root, namespaces):
    lagebeztxt_dict = {}
    for tag in ['AX_LagebezeichnungMitHausnummer', 'AX_LagebezeichnungOhneHausnummer']:
        for element in root.findall(f'.//adv:{tag}', namespaces):
            gml_id = element.get('{http://www.opengis.net/gml/3.2}id')
            unverschluesselt = element.find('.//adv:unverschluesselt', namespaces)
            hausnummer = element.find('.//adv:hausnummer', namespaces)
            
            if unverschluesselt is not None:
                if hausnummer is not None:
                    lagebeztxt_dict[gml_id] = f"{unverschluesselt.text} {hausnummer.text}"
                else:
                    lagebeztxt_dict[gml_id] = unverschluesselt.text
            else:
                lagebeztxt_dict[gml_id] = "<null>"
    
    return lagebeztxt_dict

# Process a single AX_Flurstueck element
def process_single_flurstueck(flurstueck, namespaces, lookup_dicts):
    # Extracting coordinates in bulk
    polygon_coords = [coord for posList in flurstueck.findall('.//gml:posList', namespaces)
                      for coord in extract_coordinates(posList.text)]
    polygon = Polygon(polygon_coords)
    
    # Extract attributes in a single pass
    flaeche = flurstueck.find('.//adv:amtlicheFlaeche', namespaces)
    flaeche = flaeche.text if flaeche is not None else None
    
    flstkennz = flurstueck.find('.//adv:flurstueckskennzeichen', namespaces)
    flstkennz = flstkennz.text if flstkennz is not None else None

    zaehler = flurstueck.find('.//adv:zaehler', namespaces).text
    nenner = flurstueck.find('.//adv:nenner', namespaces)
    flurstnr = create_flurstnr(zaehler, nenner.text if nenner is not None else None)

    # Gemeindeschlüssel extraction
    gemeindekennzeichen = flurstueck.find('.//adv:AX_Gemeindekennzeichen', namespaces)
    if gemeindekennzeichen is not None:
        land = gemeindekennzeichen.find('.//adv:land', namespaces).text
        kreis = gemeindekennzeichen.find('.//adv:kreis', namespaces).text
        regierungsbezirk = gemeindekennzeichen.find('.//adv:regierungsbezirk', namespaces).text
        gemeinde_code = gemeindekennzeichen.find('.//adv:gemeinde', namespaces).text
        gmdschl = create_gmdschl(land, regierungsbezirk, kreis, gemeinde_code)
    else:
        gmdschl = None
        land = None
        regierungsbezirk = None
        gemeinde_code = None

    # Use the lookup dictionaries for faster data retrieval
    merged_value = f"{land}{regierungsbezirk}{kreis}"
    kreis_bezeichnung = lookup_dicts['kreis'].get(merged_value, "<null>")

    regbezirk_key = f"{land}{regierungsbezirk}" if land and regierungsbezirk else None
    regbezirk_bezeichnung = lookup_dicts['regbezirk'].get(regbezirk_key, "<null>")

    gemeinde = lookup_dicts['gemeinde'].get(merged_value + gemeinde_code, "<null>") if gemeindekennzeichen is not None else "<null>"
    land_name = lookup_dicts['land'].get(land, "<null>") if land else "<null>"
    
    gemarkungsnummer = flurstueck.find('.//adv:AX_Gemarkung_Schluessel/adv:gemarkungsnummer', namespaces)
    gemarkung = lookup_dicts['gemarkung'].get(f"{land}{gemarkungsnummer.text}", "<null>") if land is not None and gemarkungsnummer is not None else "<null>"

    # Extract lagebeztxt using the lookup dictionary
    weist_auf = flurstueck.find('.//adv:weistAuf[@xlink:href]', namespaces)
    zeigt_auf = flurstueck.find('.//adv:zeigtAuf[@xlink:href]', namespaces)
    
    if weist_auf is not None:
        href = weist_auf.get('{http://www.w3.org/1999/xlink}href')
        lagebeztxt = lookup_dicts['lagebeztxt'].get(href.split(":")[-1], "<null>")
    elif zeigt_auf is not None:
        href = zeigt_auf.get('{http://www.w3.org/1999/xlink}href')
        lagebeztxt = lookup_dicts['lagebeztxt'].get(href.split(":")[-1], "<null>")
    else:
        lagebeztxt = "<null>"

    # Return the extracted data as a dictionary
    return {
        'geometry': polygon,
        'flaeche': flaeche,
        'flstkennz': flstkennz,
        'flur': 'Flur',
        'flurstnr': flurstnr,
        'gmdschl': gmdschl,
        'regbezirk': regbezirk_bezeichnung,
        'kreis': kreis_bezeichnung,
        'gemeinde': gemeinde,
        'land': land_name,
        'gemarkung': gemarkung,
        'lagebeztxt': lagebeztxt
    }

# Process all AX_Flurstueck tags with optimizations
def process_flurstueck(root):
    namespaces = {'gml': 'http://www.opengis.net/gml/3.2',
                  'adv': 'http://www.adv-online.de/namespaces/adv/gid/6.0',
                  'xlink': 'http://www.w3.org/1999/xlink'}
    
    # Create lookup dictionaries
    lookup_dicts = {
        'kreis': find_kreis(root, namespaces),
        'regbezirk': find_regbezirk(root, namespaces),
        'gemeinde': create_lookup_dict(root, 'AX_Gemeinde', './/adv:schluesselGesamt', './/adv:bezeichnung', namespaces),
        'land': create_lookup_dict(root, 'AX_Bundesland', './/adv:schluesselGesamt', './/adv:bezeichnung', namespaces),
        'gemarkung': create_lookup_dict(root, 'AX_Gemarkung', './/adv:schluesselGesamt', './/adv:bezeichnung', namespaces),
        'lagebeztxt': create_lagebeztxt_dict(root, namespaces)
    }
    
    # Use multiprocessing to process Flurstueck elements in parallel
    with mp.Pool() as pool:
        data = pool.starmap(
            process_single_flurstueck,
            [(flurstueck, namespaces, lookup_dicts) for flurstueck in root.findall('.//adv:AX_Flurstueck', namespaces)]
        )
    
    return data

# Main function
def main(xml_file, output_shapefile):
    start_time = time.time()
    root = parse_xml(xml_file)
    data = process_flurstueck(root)
    
    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(data)
    gdf.set_crs(epsg=25832, inplace=True)  # Set appropriate CRS
    
    # Save to a shapefile
    gdf.to_file(output_shapefile, driver='ESRI Shapefile')
    
    # Save the .prj file with the specified projection
    prj_content = ('PROJCS["ETRS89 / UTM zone 32N",'
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
    
    prj_file = output_shapefile.replace('.shp', '.prj')
    with open(prj_file, 'w') as prj:
        prj.write(prj_content)
    
    end_time = time.time()
    print(f"Processing complete. Shapefile saved as '{output_shapefile}'. Time taken: {end_time - start_time:.2f} seconds.")

# Example usage
if __name__ == "__main__":
    xml_file = sys.argv[1]
    output_shapefile = sys.argv[2]
    main(xml_file, output_shapefile)