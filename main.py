import subprocess
import time

def run_script(script_name, *args):
    command = ['python', script_name] + list(args)
    start_time = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    end_time = time.time()
    elapsed_time = end_time - start_time
    if result.returncode != 0:
        print(f"Error running {script_name}: {result.stderr}")
    else:
        print(f"Successfully ran {script_name} in {elapsed_time:.2f} seconds")
    return elapsed_time

if __name__ == "__main__":
    # Define file paths
    xml_file = "1546621_0.xml"
    bez_dict_file = "bez_dict.json"
    flurstueck_shapefile = "flurstueck.shp"
    nutzung_shapefile = "nutzung.shp"
    nutzung_flurstueck_shapefile = "nutzungFlurstueck.shp"
    gebauede_bauwerk_shapefile = "gebauedeBauwerk.shp"
    verwaltungs_einheit_shapefile = "verwaltungsEinheit.shp"
    kataster_bezirk_shapefile = "katasterBezirk.shp"

    # Track total execution time
    total_start_time = time.time()

    # Run scripts in the correct order
    total_time = 0
    total_time += run_script('flurstueck.py', xml_file, flurstueck_shapefile)
    total_time += run_script('nutzung.py', xml_file, bez_dict_file, nutzung_shapefile)
    total_time += run_script('nutflu.py', flurstueck_shapefile, nutzung_shapefile, nutzung_flurstueck_shapefile)
    total_time += run_script('guby.py', xml_file, gebauede_bauwerk_shapefile)
    total_time += run_script('ver.py', flurstueck_shapefile, xml_file, verwaltungs_einheit_shapefile)
    total_time += run_script('kat.py', flurstueck_shapefile, kataster_bezirk_shapefile)

    total_end_time = time.time()
    total_elapsed_time = total_end_time - total_start_time

    print(f"Total execution time: {total_elapsed_time:.2f} seconds")