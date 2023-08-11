# Insert_implantation.py

from __future__ import annotations

import PySimpleGUI as sg
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


sg.theme("LightGreen3")

layout = [[[sg.Text("Insert implantation into datajoint table", font=("Helvetica", 16))]],
        [sg.Text("Subject ID"), sg.InputText()],
        [sg.Text("Surgeon"), sg.InputText()],
        [sg.Text("Date of implant"), sg.InputText(key="doi")],
        [sg.CalendarButton("Choose", target="doi", format="%Y-%m-%d")],
        [sg.Text("Implant type"), sg.InputCombo(["fiber", "ephys"])],
        [sg.Text("Brain Region"), sg.InputText()],
        [sg.Text("A/P"), sg.InputText()],
        [sg.Text("A/P reference"), sg.InputCombo(["bregma", "lambda"], size=(10, 1))],
        [sg.Text("M/L"), sg.InputText()],
        [sg.Text("D/V"), sg.InputText()],
        [sg.Text("D/V reference"), sg.InputCombo(["skull_surface", "dura"], size=(10, 1))],

        [sg.Button("Insert to Right Hemisphere"), sg.Button("Insert to Left Hemisphere")],
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

    elif event == "Insert another implantation":
        clear_fields()
    elif event == "Quit":
        break

window.close()
