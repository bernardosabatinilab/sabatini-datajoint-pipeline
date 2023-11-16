#makeTOML.py

import os
import PySimpleGUI as sg
import pandas as pd
import numpy as np
import warnings
from pathlib import Path
import toml

def save_to_toml(data, filename):
    with open(filename, 'w') as toml_file:
        toml.dump(data, toml_file)

sg.theme("DefaultNoMoreNagging")

layout = [[[sg.Text("Create processing TOML file for photometry analysis", font=("Helvetica", 16))]],
        [[sg.Text("Processing Parameters", font=("Helvetica", 14))]],
        [sg.Text("Subject ID"), sg.InputText(key="Subject ID")],
        [sg.Text("Behavior Offset"), sg.InputText(key="Behavior Offset")],
        [sg.Text("Final z-score?"), sg.InputCombo(["true", "false"], size=(10, 1), key="Final z-score?")],
        [sg.Text("Z-score window"), sg.InputText(key="Z-score window")],
        [sg.Text("Bandpass bandwidth for hilbert"), sg.InputText(key="Bandpass bandwidth for hilbert")],
        [sg.Text("Sampling frequency"), sg.InputText(key="Sampling frequency")],
        [sg.Text("Downsampling frequency"), sg.InputText(key="Downsampling frequency")],
        [sg.Text("Transform type"), sg.InputCombo(["spectrogram", "hilbert"], size=(10, 1), key="Transform type")],
        [sg.Text("no per segment"), sg.InputText(key="no per segment")],
        [sg.Text("carrier freq - green channel"), sg.InputText(key="carrier freq - green channel")],
        [sg.Text("carrier freq - red channel"), sg.InputText(key="carrier freq - red channel")],
        [sg.Button("Insert to Right Hemisphere"), sg.Button("Insert to Left Hemisphere")],
        
        [[sg.Text("Input signal indices for proper indexing - zero indexed", font=("Helvetica", 14))]],
        [sg.Text("total channels"), sg.InputText(key="total_channels")],
        [sg.Text("emission wavelength - green"), sg.InputText(key="emission wavelength - green")],
        [sg.Text("emission wavelength - red"), sg.InputText(key="emission wavelength - red")],
        [sg.Text("excitation wavelength - green"), sg.InputText(key="excitation wavelength - green")],
        [sg.Text("excitation wavelength - red"), sg.InputText(key="excitation wavelength - red")],
        [sg.Text("green sensor protein used"), sg.InputText(key="green sensor protein used")],
        [sg.Text("red sensor protein used"), sg.InputText(key="red sensor protein used")],
        [sg.Text("photometry index for green channel"), 
            sg.InputCombo(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "None"], size=(10, 1),
            key="photometry index for green channel")],
        [sg.Text("photometry index for red channel"), 
            sg.InputCombo(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "None"], size=(10, 1),
            key="photometry index for red channel")],
        [sg.Text("carrier index for green channel"), 
            sg.InputCombo(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "None"], size=(10, 1),
            key="carrier index for green channel")],
        [sg.Text("carrier index for red channel"), 
            sg.InputCombo(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "None"], size=(10, 1), 
            key="carrier index for red channel")],
        [sg.Button("Insert to Right Signal Indices"), sg.Button("Insert to Left Signal Indices")],

        [sg.Button("Save"), sg.Button("Exit")]]

window = sg.Window("TOML file creator", layout)

Fiber = {
    'light_source': "",
    'fiber_type': "",
    'fiber_diameter': "",
    'implantation': { 'date': "",
                     'surgeon': "",
                     'left': {'brain_region': "",
                              'notes': "", },
                     'right': {'brain_region': "",
                               'notes': "", }, },
    
}

Processing_Parameters = {
    'left': {
        'carrier_frequency_g': None,
        'carrier_frequency_r': None,
    }, 
    'right': {
        'carrier_frequency_g': None,
        'carrier_frequency_r': None,
    },
}

Signal_Indices = {
                'left': {
        'emission_wavelength': {"green" : None, "red" : None},
        'excitation_wavelength': {"green" : None, "red" : None},
        'sensor_protein': {"green" : None, "red" : None},
        'photom_g': None,
        'photom_r': None,
        'carrier_g': None,
        'carrier_r': None
    }, 
    'right': {
        'emission_wavelength': {"green" : None, "red" : None},
        'excitation_wavelength': {"green" : None, "red" : None},
        'sensor_protein': {"green" : None, "red" : None},
        'photom_g': None,
        'photom_r': None,
        'carrier_g': None,
        'carrier_r': None
    },
}


while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED or event == "Exit":
        break

    if event == "Insert to Left Hemisphere":
        Processing_Parameters['left']['carrier_frequency_g'] = float(values['carrier freq - green channel'])
        Processing_Parameters['left']['carrier_frequency_r'] = float(values['carrier freq - red channel'])
        print("inserted left processing parameters")
    if event == "Insert to Right Hemisphere":
            Processing_Parameters['right']['carrier_frequency_g'] = float(values['carrier freq - green channel'])
            Processing_Parameters['right']['carrier_frequency_r'] = float(values['carrier freq - red channel'])
            print("inserted right processing parameters")

    if event == "Insert to Left Signal Indices":
                Signal_Indices['left']['emission_wavelength']['green'] = int(values['emission wavelength - green'])
                Signal_Indices['left']['emission_wavelength']['red'] = int(values['emission wavelength - red'])
                Signal_Indices['left']['excitation_wavelength']['green'] = int(values['excitation wavelength - green'])
                Signal_Indices['left']['excitation_wavelength']['red'] = int(values['excitation wavelength - red'])
                Signal_Indices['left']['sensor_protein']['green'] = values['green sensor protein used']
                Signal_Indices['left']['sensor_protein']['red'] = values['red sensor protein used']
                Signal_Indices['left']['photom_g'] = int(values['photometry index for green channel']) if values['photometry index for green channel'] != "None" else None
                Signal_Indices['left']['photom_r'] = int(values['photometry index for red channel']) if values['photometry index for red channel'] != "None" else None
                Signal_Indices['left']['carrier_g'] = int(values['carrier index for green channel']) if values['carrier index for green channel'] != "None" else None
                Signal_Indices['left']['carrier_r'] = int(values['carrier index for red channel']) if values['carrier index for red channel'] != "None" else None
                print("inserted left signal indices")

    if event == "Insert to Right Signal Indices":
                Signal_Indices['right']['emission_wavelength']['green'] = int(values['emission wavelength - green'])
                Signal_Indices['right']['emission_wavelength']['red'] = int(values['emission wavelength - red'])
                Signal_Indices['right']['excitation_wavelength']['green'] = int(values['excitation wavelength - green'])
                Signal_Indices['right']['excitation_wavelength']['red'] = int(values['excitation wavelength - red'])
                Signal_Indices['right']['sensor_protein']['green'] = values['green sensor protein used']
                Signal_Indices['right']['sensor_protein']['red'] = values['red sensor protein used']
                Signal_Indices['right']['photom_g'] = int(values['photometry index for green channel']) if values['photometry index for green channel'] != "None" else None
                Signal_Indices['right']['photom_r'] = int(values['photometry index for red channel']) if values['photometry index for red channel'] != "None" else None
                Signal_Indices['right']['carrier_g'] = int(values['carrier index for green channel']) if values['carrier index for green channel'] != "None" else None
                Signal_Indices['right']['carrier_r'] = int(values['carrier index for red channel']) if values['carrier index for red channel'] != "None" else None
                print("inserted right signal indices")

    if event == "Save":
        subject_ID = values['Subject ID']
        Processing_Parameters.update({
                'behavior_offset': float(values['Behavior Offset']),
                'final_z': values['Final z-score?'],
                'z_window': float(values['Z-score window']),
                'bandpass_bandwidth': float(values['Bandpass bandwidth for hilbert']),
                'sampling_frequency': float(values['Sampling frequency']),
                'downsample_frequency': float(values['Downsampling frequency']),
                'transform': values['Transform type'],
                'no_per_segment': int(values['no per segment']),
                'no_overlap': int(values['no per segment'])//2,
                })

        Signal_Indices.update({
                'total_channels': int(values['total_channels'])})


        data = { 'Subject_ID': subject_ID,
                'Fiber': Fiber,
                'Processing_Parameters': Processing_Parameters,
                'Signal_Indices': Signal_Indices
                }
                
        
        filename = sg.popup_get_file("Save TOML file", save_as=True, file_types=(("TOML Files", "*.toml"),))

        if filename:
            save_to_toml(data, filename)
            sg.popup("File saved successfully!")

window.close()
