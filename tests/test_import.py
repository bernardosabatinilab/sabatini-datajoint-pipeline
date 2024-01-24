import logging
import importlib

def test_import():
    
    repo_packs = [
        'pandas',
        'numpy',
        'scipy',
        'sklearn',
        'matplotlib',
        'seaborn',
        'datajoint',
        'tensorflow',
        'pymatreader',
        'tomli', 
        'yaml',
        'tdt',
        'deeplabcut',
    ]

    for pack in repo_packs:
        try:
            importlib.import_module(pack)
        except ImportError:
            logging.warning(f'Could not import {pack}.')
            continue


def test_workflow_packages():
    try: 
        importlib.import_module('workflow.utils.demodulation')
    except ImportError:
        logging.warning('Could not import demod from photometry pipeline.')
        pass

def test_elements_pack():
    element_list = [
        'element_array_ephys',
        'element_deeplabcut',
        'element_interface',
        'element_calcium_imaging',
        'element_animal',
        'element_lab',
        'element_session',
        'element_event',
    ]

    for element in element_list:
        try:
            importlib.import_module(element)
        except ImportError:
            logging.warning('Could not import {element}.')
            pass

