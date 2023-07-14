# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
from pathlib import Path
_dir_parent = Path(__file__).parent.parent.parent

import os
import sys
## add all subdirectories to sys.path
def add_subdirs_to_sys_path(path):
    for _dir in path.iterdir():
        if _dir.name[:2] in ['__pycache__', '.ipynb_checkpoints']:
            continue
        if _dir.is_dir():
            # print(f'Adding {_dir} to sys.path')
            sys.path.insert(0, str(_dir))
            add_subdirs_to_sys_path(_dir)
sys.path.insert(0, str(_dir_parent))
add_subdirs_to_sys_path(_dir_parent)

project = 'sabatini-datajoint'
copyright = '2023, Datajoint, Janet Berrios'
author = 'Datajoint, Janet Berrios'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',  # allows automatic parsing of docstrings
    'sphinx.ext.mathjax',  # allows mathjax in documentation
    'sphinx.ext.viewcode',  # links documentation to source code
    'sphinx.ext.githubpages',  # allows integration with github
    'sphinx.ext.napoleon',  # parsing of different docstring styles
    'sphinx.ext.coverage',  # allows coverage of docstrings
    'sphinx.ext.autosectionlabel',  # allows linking to sections using :ref:
]

templates_path = ['_templates']
source_suffix = ['.rst', '.md']
exclude_patterns = ['_build']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
#html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'sabatini-datajoint-doc'

def setup(app):
    app.add_css_file('css/custom.css')