import streamlit as st
import subprocess
import os
import time

def run_script(script_name, *args):
    command = ['python', script_name] + list(args)
    start_time = time.time()
    result = subprocess.run(command, capture_output=True, text=True)
    end_time = time.time()
    elapsed_time = end_time - start_time
    if result.returncode != 0:
        return f"Error running {script_name}: {result.stderr}"
    else:
        return f"Successfully ran {script_name} in {elapsed_time:.2f} seconds"

def process_files(xml_file, output_path):
    # Define file paths
    bez_dict_file = "bez_dict.json"
    flurstueck_shapefile = os.path.join(output_path, "flurstueck.shp")
    nutzung_shapefile = os.path.join(output_path, "nutzung.shp")
    nutzung_flurstueck_shapefile = os.path.join(output_path, "nutzungFlurstueck.shp")
    gebauede_bauwerk_shapefile = os.path.join(output_path, "gebauedeBauwerk.shp")
    verwaltungs_einheit_shapefile = os.path.join(output_path, "verwaltungsEinheit.shp")
    kataster_bezirk_shapefile = os.path.join(output_path, "katasterBezirk.shp")

    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)

    # Run scripts in the correct order
    results = []
    results.append(run_script('flurstueck.py', xml_file, flurstueck_shapefile))
    results.append(f"Generated: {flurstueck_shapefile}")
    results.append(run_script('nutzung.py', xml_file, bez_dict_file, nutzung_shapefile))
    results.append(f"Generated: {nutzung_shapefile}")
    results.append(run_script('nutflu.py', flurstueck_shapefile, nutzung_shapefile, nutzung_flurstueck_shapefile))
    results.append(f"Generated: {nutzung_flurstueck_shapefile}")
    results.append(run_script('guby.py', xml_file, gebauede_bauwerk_shapefile))
    results.append(f"Generated: {gebauede_bauwerk_shapefile}")
    results.append(run_script('ver.py', flurstueck_shapefile, xml_file, verwaltungs_einheit_shapefile))
    results.append(f"Generated: {verwaltungs_einheit_shapefile}")
    results.append(run_script('kat.py', flurstueck_shapefile, kataster_bezirk_shapefile))
    results.append(f"Generated: {kataster_bezirk_shapefile}")

    results.append("CONVERSION COMPLETED")

    return "\n".join(results)

# Streamlit app
st.title("NAS-ALKIS Conversion")
st.write("Upload an XML file and specify the output path to generate conversion.")

# File uploader for XML file
xml_file = st.file_uploader("Input XML File", type=["xml"])

# Text input for output path
output_path = st.text_input("Output Path", placeholder="Enter the output directory path")

# Button to start the conversion process
if st.button("Start Conversion"):
    if xml_file is not None and output_path:
        try:
            # Ensure the output directory exists
            os.makedirs(output_path, exist_ok=True)
            
            # Save the uploaded XML file to the specified location
            xml_file_path = os.path.join(output_path, xml_file.name)
            with open(xml_file_path, "wb") as f:
                f.write(xml_file.getbuffer())

            # Process the files
            result = process_files(xml_file_path, output_path)
            st.text(result)
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.error("Please upload an XML file and specify the output path.")
