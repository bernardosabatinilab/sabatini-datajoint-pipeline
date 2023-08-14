#Wrapper for GUI launch

import PySimpleGUI as sg
import os


sg.theme("DefaultNoMoreNagging")

layout = [[[sg.Text("Select GUI to launch", font=("Helvetica", 18))]],
        [sg.Button("Mouse"), sg.Button("Virus"), sg.Button("Implantation"), sg.Button("Make a TOML file")],
        [sg.Button("Quit", pad=((5, (10, 0))))]]


window = sg.Window("GUI launcher", layout)


while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        break
    if event == "Mouse":
        os.system("python TOML-metafile-scripts\Insert_mouse.py")
    if event == "Virus":
        os.system("python TOML-metafile-scripts\Insert_virus.py")
    if event == "Implantation":
        os.system("python TOML-metafile-scripts\Insert_implantation.py")
    if event == "Make a TOML file":
        os.system("python TOML-metafile-scripts\makeTOML.py")
    if event == "Quit":
        break

window.close()

