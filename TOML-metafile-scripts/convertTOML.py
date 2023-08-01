#Convert .json to .toml for metadata files

import json
import tomlkit
import glob



def process_fields(data):
    for side in ["left", "right"]:
        if "Signal_Indices" in data and side in data["Signal_Indices"]:
            for field in ["photom_g", "photom_r", "carrier_g", "carrier_r"]:
                if field in data["Signal_Indices"][side]:
                    if data["Signal_Indices"][side][field] == -1:
                        data["Signal_Indices"][side][field] = "None"


json_files = glob.glob("*output.json")


for json_file in json_files:
    with open(json_file, 'r') as f:
        json_data = json.load(f)

    # Process emission_wavelength and excitation_wavelength strings
    process_fields(json_data)

    toml_data = tomlkit.dumps(json_data)

    toml_file = json_file.replace(".json", ".toml")

    with open(toml_file, 'w') as f:
        f.write(toml_data)

print(".json to .toml conversion complete! Please change your dictionaries if needed.")

