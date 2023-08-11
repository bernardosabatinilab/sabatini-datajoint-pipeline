# Insert_virus.py

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
import random
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
    window[9].update('')
    window[10].update('')

sg.theme("LightGreen1")

layout = [[[sg.Text("Insert viral injection into datajoint tables", font=("Helvetica", 16))]],
        [sg.Text("Subject ID"), sg.InputText()],
        [sg.Text("Experimenter"), sg.InputText()],
        [sg.Text("Date of injection"), sg.InputText(key="doi")],
        [sg.CalendarButton("Choose", target="doi", format="%Y-%m-%d")],
        [sg.Text("Virus"), sg.InputText()],
        [sg.Text("Volume"), sg.InputText()],
        [sg.Text("Brain Region"), sg.InputText()],
        [sg.Text("A/P"), sg.InputText()],
        [sg.Text("A/P reference"), sg.InputCombo(["bregma", "lambda"], size=(10, 1))],
        [sg.Text("M/L"), sg.InputText()],
        [sg.Text("D/V"), sg.InputText()],
        [sg.Text("D/V reference"), sg.InputCombo(["skull_surface", "dura"], size=(10, 1))],
        [sg.Text("Notes"), sg.InputText()],

        [sg.Button("Insert to Right Hemisphere"), sg.Button("Insert to Left Hemisphere")],
        [sg.Button("Insert another viral injection"), sg.Button("Quit")]]

window = sg.Window("Virus DJ Insertion", layout)

while True: 
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    if event == "Insert to Right Hemisphere":
        subject_id = values[0]
        experimenter = values[1]
        doi = values["doi"]
        virus = values[2]
        volume = values[3]
        brain_region = values[4]
        ap = values[5]
        ap_ref = values[6]
        ml = values[7]
        dv = values[8]
        dv_ref = values[9]
        notes = values[10]
        injection_id = random.randint(1, 100)

        key = (subject.Subject & {'subject': subject_id}).fetch1('KEY')

        #populate lookup tables first for virus, user, and brain region
        reference.Virus.insert1(dict(name=virus), skip_duplicates=True)
        lab.User.insert1(dict(user=experimenter), skip_duplicates=True)
        reference.BrainRegion.insert1(dict(region_name=brain_region), skip_duplicates=True)


        user_key = (lab.User & {'user': experimenter}).fetch1('KEY')
        regionKey = (reference.BrainRegion & {'region_name': brain_region}).fetch1('KEY')

        injection_list = dict(subject = key['subject'],
                             injection_id = injection_id,
                             user = user_key['user'],
                             name = virus, injection_volume = volume, 
                             brain_region = regionKey['region_name'], 
                             hemisphere = 'right', notes = notes)
        reference.VirusInjection.insert1(injection_list, skip_duplicates=True)


        coordinates_list = dict(subject = key['subject'],
                                injection_id = injection_id,
                                ap = ap, ap_ref = ap_ref,
                                ml = ml, ml_ref = 'sagittal_suture',
                                dv = dv, dv_ref = dv_ref)
        reference.VirusInjection.Coordinate.insert1(coordinates_list, skip_duplicates=True)
        print("Inserted to right hemisphere")

    if event == "Insert to Left Hemisphere":
        subject_id = values[0]
        experimenter = values[1]
        doi = values["doi"]
        virus = values[2]
        volume = values[3]
        brain_region = values[4]
        ap = values[5]
        ap_ref = values[6]
        ml = values[7]
        dv = values[8]
        dv_ref = values[9]
        notes = values[10]
        injection_id = random.randint(1, 100)

        key = (subject.Subject & {'subject': subject_id}).fetch1('KEY')

        #populate lookup tables first for virus, user, and brain region
        reference.Virus.insert1(dict(name=virus), skip_duplicates=True)
        lab.User.insert1(dict(user=experimenter), skip_duplicates=True)
        reference.BrainRegion.insert1(dict(region_name=brain_region), skip_duplicates=True)


        user_key = (lab.User & {'user': experimenter}).fetch1('KEY')
        regionKey = (reference.BrainRegion & {'region_name': brain_region}).fetch1('KEY')

        injection_list = dict(subject = key['subject'],
                             injection_id = injection_id,
                             user = user_key['user'],
                             name = virus, injection_volume = volume, 
                             brain_region = regionKey['region_name'], 
                             hemisphere = 'left', notes = notes)

        reference.VirusInjection.insert1(injection_list, skip_duplicates=True)


        coordinates_list = dict(subject = key['subject'],
                                injection_id = injection_id,
                                ap = ap, ap_ref = ap_ref,
                                ml = ml, ml_ref = 'sagittal_suture',
                                dv = dv, dv_ref = dv_ref)

        reference.VirusInjection.Coordinate.insert1(coordinates_list, skip_duplicates=True)
        print("Inserted to left hemisphere")

    elif event == "Insert another viral injection":
        clear_fields() 

    elif event == "Quit":
        break

window.close()
