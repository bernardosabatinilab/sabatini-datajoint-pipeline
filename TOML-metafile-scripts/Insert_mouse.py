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
    window['strain'].update('')
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
    window[11].update('')
    window[12].update('')


sg.theme("LightGreen2")

layout = [[[sg.Text("Insert subject into datajoint table", font=("Helvetica", 16))]],
        [sg.Text("Subject ID"), sg.InputText()],
        [sg.Text("Date of birth"), sg.InputText(key="dob"), sg.CalendarButton("Choose", target="dob", format="%Y-%m-%d")],
        [sg.Text("Sex"), sg.InputCombo(["M", "F", "U"], size=(10, 1))],
        [sg.Text("Strain"), sg.InputText(key="strain")],
        [sg.Text("Allele - 1"), sg.InputText(), sg.Text("Zygosity - 1"), sg.InputCombo(["Homozygous", "Heterozygous", "Present", "Absent"], size=(10, 1))],
        [sg.Text("Allele - 2"), sg.InputText(), sg.Text("Zygosity - 2"), sg.InputCombo(["Homozygous", "Heterozygous", "Present", "Absent"], size=(10, 1))],
        [sg.Text("Allele - 3"), sg.InputText(), sg.Text("Zygosity - 3"), sg.InputCombo(["Homozygous", "Heterozygous", "Present", "Absent"], size=(10, 1))],
        [sg.Text("Allele - 4"), sg.InputText(), sg.Text("Zygosity - 4"), sg.InputCombo(["Homozygous", "Heterozygous", "Present", "Absent"], size=(10, 1))],
        [sg.Text("Allele - 5"), sg.InputText(), sg.Text("Zygosity - 5"), sg.InputCombo(["Homozygous", "Heterozygous", "Present", "Absent"], size=(10, 1))],
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
        strain = values["strain"]
        sex = values[1]
        allele1 = values[2]
        zygosity1 = values[3]
        allele2 = values[4]
        zygosity2 = values[5]
        allele3 = values[6]
        zygosity3 = values[7]
        allele4 = values[8]
        zygosity4 = values[9]
        allele5 = values[10]
        zygosity5 = values[11]
        description = values[12]

        subject.Subject.insert1(dict(subject=subject_id,
                       sex=sex, 
                       subject_birth_date=dob, 
                       subject_description= description
                       ), skip_duplicates=True)
        
        #populate lookup tables
        key = (subject.Subject & {'subject': subject_id}).fetch1('KEY')
        subject.Strain.insert1(dict(strain = strain, strain_standard_name = '', strain_desc = ''), skip_duplicates=True)
        strainKey = (subject.Strain & {'strain': strain}).fetch1('KEY')

        subject.Subject.Strain.insert1(dict(subject = key['subject'], strain = strainKey['strain']), skip_duplicates=True)

        allele_list = [allele1, allele2, allele3, allele4, allele5]
        zygosity_list = [zygosity1, zygosity2, zygosity3, zygosity4, zygosity5]

        for allele in allele_list:
            if allele == '':
                continue
            else:
                subject.Allele.insert1(dict(allele=allele), skip_duplicates=True)
        
        for allele, zygosity in zip(allele_list, zygosity_list):
            if allele == '':
                continue
            else:
                genotype_list = dict(subject = key['subject'], allele = allele, zygosity = zygosity)
                subject.Zygosity.insert1(genotype_list, skip_duplicates=True)


        print('Inserted subject information for:', subject_id)

    elif event == "Insert another subject":
        clear_fields()
    elif event == "Quit":
        break
        
window.close()