# Insert_mouse.py

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
    window['dob'].update('')
    window[0].update('')
    window[1].update('')
    window[2].update('')
    window[3].update('')
    window[4].update('')

sg.theme("LightGreen2")

layout = [[[sg.Text("Insert subject into datajoint table", font=("Helvetica", 16))]],
        [sg.Text("Subject ID"), sg.InputText()],
        [sg.Text("Date of birth"), sg.InputText(key="dob")],
        [sg.CalendarButton("Choose", target="dob", format="%Y-%m-%d")],
        [sg.Text("Sex"), sg.InputCombo(["M", "F", "U"], size=(10, 1))],
        [sg.Text("Genotype"), sg.InputText()],
        [sg.Text("Zygosity"), sg.InputCombo(["Homozygous", "Heterozygous", "Present", "Absent"], size=(10, 1))],
        [sg.Text("Description"), sg.InputText()],
        [sg.Button("Insert"), sg.Button("Insert another subject"), sg.Button("Quit")]]

window = sg.Window("Mouse DJ Insertion", layout)


while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    if event == "Insert":
        subject_id = values[0]
        dob = values["dob"]
        sex = values[1]
        genotype = values[2]
        zygosity = values[3]
        description = values[4]

        subject.Subject.insert1(dict(subject=subject_id,
                       sex=sex, 
                       subject_birth_date=dob, 
                       subject_description= description
                       ), skip_duplicates=True)

        key = (subject.Subject & {'subject': subject_id}).fetch1('KEY')

        subject.Allele.insert1(dict(allele=genotype), skip_duplicates=True)

        genotype_list = dict(subject = key['subject'], allele = genotype, zygosity = zygosity)
        subject.Zygosity.insert1(genotype_list, skip_duplicates=True)


        print('Inserted subject information for:', subject_id)
    elif event == "Insert another subject":
        clear_fields()
    elif event == "Quit":
        break
        
window.close()