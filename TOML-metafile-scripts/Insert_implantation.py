# Insert_implantation.py

from __future__ import annotations

import PySimpleGUI as sg
import json
import datajoint as dj

import os
dj.config.load('dj_local_config.json')
dj.conn()
import datajoint as dj
import pandas as pd
import numpy as np
import warnings
from pathlib import Path

from element_interface.utils import find_full_path
from workflow import db_prefix
from workflow.pipeline import session, subject, lab, reference, ingestion
from workflow.utils.paths import get_raw_root_data_dir

def clear_fields():
    window['doi'].update('')
    window[0].update('')
    window[1].update('')
    window[2].update('')
    window[3].update('')
    window[4].update('')
    window[5].update('')
    window[6].update('')
    window[7].update('')
    window[8].update('')

def save_defaults(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)


sg.theme("LightGreen3")

layout = [[[sg.Text("Insert implantation into datajoint table", font=("Helvetica", 16))]],
        [sg.Text("Subject ID"), sg.InputText()],
        [sg.Text("Surgeon"), sg.InputText()],
        [sg.Text("Date of implant"), sg.InputText(key="doi"), sg.CalendarButton("Choose", target="doi", format="%Y-%m-%d")],
        [sg.Text("Implant type"), sg.InputCombo(["fiber", "ephys"])],
        [sg.Text("Brain Region"), sg.InputText()],
        [sg.Text("A/P"), sg.InputText()],
        [sg.Text("A/P reference"), sg.InputCombo(["bregma", "lambda"], size=(10, 1))],
        [sg.Text("M/L"), sg.InputText()],
        [sg.Text("D/V"), sg.InputText()],
        [sg.Text("D/V reference"), sg.InputCombo(["skull_surface", "dura"], size=(10, 1))],

        [sg.Button("Insert to Right Hemisphere"), sg.Button("Insert to Left Hemisphere")],
        [sg.Button("Save left coordinates as defaults"), sg.Button("Save right coordinates as defaults")],
        [sg.Button("Load Left defaults"), sg.Button("Load Right defaults")],
        [sg.Button("Insert another implantation"), sg.Button("Quit")]]

window = sg.Window("Virus DJ Insertion", layout)

while True: 
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    if event == "Insert to Right Hemisphere":
        subject_id = values[0]
        surgeon = values[1]
        doi = values["doi"]
        implant_type = values[2]
        brain_region = values[3]
        ap = values[4]
        ap_ref = values[5]
        ml = values[6]
        dv = values[7]
        dv_ref = values[8]
        ml_ref = 'sagittal_suture'

        key = (subject.Subject & {'subject': subject_id}).fetch1('KEY')

        #populate lookup tables for implantation_type and brain_region
        reference.ImplantationType.insert1(dict(implant_type=implant_type), skip_duplicates=True)
        reference.BrainRegion.insert1(dict(region_name=brain_region), skip_duplicates=True)

        #retrieve BrainRegion and ImplantationType keys
        brainRegion_key = (reference.BrainRegion & {'region_name': brain_region}).fetch1('KEY')
        implantType_key = (reference.ImplantationType & {'implant_type': implant_type}).fetch1('KEY')

        #insert into Implantation table
        implantation_list = dict(subject = key['subject'],
                                    implant_date = doi,
                                    implant_type = implantType_key['implant_type'],
                                    brain_region = brainRegion_key['region_name'],
                                    hemisphere = 'right',
                                    surgeon = surgeon,
                                    ap = ap,
                                    ap_ref = ap_ref,
                                    ml = ml,
                                    ml_ref = ml_ref,
                                    dv = dv,
                                    dv_ref = dv_ref)
        reference.Implantation.insert1(implantation_list, skip_duplicates=True)
        print('Right implantation inserted into Implantation table')

    if event == "Insert to Left Hemisphere":
        subject_id = values[0]
        surgeon = values[1]
        doi = values["doi"]
        implant_type = values[2]
        brain_region = values[3]
        ap = values[4]
        ap_ref = values[5]
        ml = values[6]
        dv = values[7]
        dv_ref = values[8]
        ml_ref = 'sagittal_suture'

        key = (subject.Subject & {'subject': subject_id}).fetch1('KEY')

        #populate lookup tables for implantation_type and brain_region
        reference.ImplantationType.insert1(dict(implant_type=implant_type), skip_duplicates=True)
        reference.BrainRegion.insert1(dict(region_name=brain_region), skip_duplicates=True)

        #retrieve BrainRegion and ImplantationType keys
        brainRegion_key = (reference.BrainRegion & {'region_name': brain_region}).fetch1('KEY')
        implantType_key = (reference.ImplantationType & {'implant_type': implant_type}).fetch1('KEY')

        #insert into Implantation table
        implantation_list = dict(subject = key['subject'],
                                    implant_date = doi,
                                    implant_type = implantType_key['implant_type'],
                                    brain_region = brainRegion_key['region_name'],
                                    hemisphere = 'left',
                                    surgeon = surgeon,
                                    ap = ap,
                                    ap_ref = ap_ref,
                                    ml = ml,
                                    ml_ref = ml_ref,
                                    dv = dv,
                                    dv_ref = dv_ref)

        reference.Implantation.insert1(implantation_list, skip_duplicates=True)
        print('Left implantation inserted into Implantation table')

    if event == "Save right coordinates as defaults":
        brain_region = values[3]
        ap = values[4]
        ap_ref = values[5]
        ml = values[6]
        dv = values[7]
        dv_ref = values[8]
        ml_ref = 'sagittal_suture'
        right_implantation_list = dict(surgeon = surgeon,
                                    brain_region = brain_region,
                                    hemisphere = 'right',
                                    ap = ap,
                                    ap_ref = ap_ref,
                                    ml = ml,
                                    ml_ref = ml_ref,
                                    dv = dv,
                                    dv_ref = dv_ref)
        filename = sg.popup_get_file("Save right corrdinates", save_as=True, file_types=(("coordinates", "*.json"),))
        if filename:
            save_defaults(right_implantation_list, filename)
            sg.popup("Right defaults saved successfully!")
    if event == "Save left coordinates as defaults":
        surgeon = values[1]
        brain_region = values[3]
        ap = values[4]
        ap_ref = values[5]
        ml = values[6]
        dv = values[7]
        dv_ref = values[8]
        ml_ref = 'sagittal_suture'
        left_implantation_list = dict(surgeon = surgeon,
                                    brain_region = brain_region,
                                    hemisphere = 'left',
                                    ap = ap,
                                    ap_ref = ap_ref,
                                    ml = ml,
                                    ml_ref = ml_ref,
                                    dv = dv,
                                    dv_ref = dv_ref)
        filename = sg.popup_get_file("Save left corrdinates", save_as=True, file_types=(("coordinates", "*.json"),))
        if filename:
            save_defaults(left_implantation_list, filename)
            sg.popup("Left defaults saved successfully!")

    if event == "Load Left defaults":
        leftDefaults = sg.popup_get_file("Load left corrdinates")
        with open(leftDefaults, 'r') as f:
            implantation_list = json.load(f)
        window[1].update(implantation_list['surgeon'])
        window[3].update(implantation_list['brain_region'])
        window[4].update(implantation_list['ap'])
        window[5].update(implantation_list['ap_ref'])
        window[6].update(implantation_list['ml'])
        window[7].update(implantation_list['dv'])
        window[8].update(implantation_list['dv_ref'])

    if event == "Load Right defaults":
        rightDefaults = sg.popup_get_file("Load right corrdinates")
        with open(rightDefaults, 'r') as f:
            implantation_list = json.load(f)
        window[1].update(implantation_list['surgeon'])
        window[3].update(implantation_list['brain_region'])
        window[4].update(implantation_list['ap'])
        window[5].update(implantation_list['ap_ref'])
        window[6].update(implantation_list['ml'])
        window[7].update(implantation_list['dv'])
        window[8].update(implantation_list['dv_ref'])        


    elif event == "Insert another implantation":
        clear_fields()
    elif event == "Quit":
        break

window.close()
