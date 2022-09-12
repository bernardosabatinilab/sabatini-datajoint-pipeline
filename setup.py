from setuptools import setup, find_packages
from os import path

pkg_name = 'workflow'
here = path.abspath(path.dirname(__file__))

long_description = """"
Pipeline for Sabatini Lab - Team DOPE
Integrated multimodality pipeline containing extracellular electrophysiology, 
Calcium Imaging, Fiber Photometry, DeepLabCut, and integrated behavior. 
Pipeline constructed using DataJoint elements:
+ [element-lab](https://github.com/datajoint/element-lab)
+ [element-animal](https://github.com/datajoint/element-animal)
+ [element-session](https://github.com/datajoint/element-session)
+ [element-array-ephys](https://github.com/datajoint/element-array-ephys)
+ [element-calcium-imaging](https://github.com/datajoint/element-calcium-imaging)
+ [element-behavior](https://github.com/datajoint/element-behavior)
+ [element-interface](https://github.com/datajoint/element-interface)
+ [datajoint-utilities](https://github.com/datajoint-company/datajoint-utilities)
"""

with open(path.join(here, 'requirements.txt')) as f:
    requirements = f.read().splitlines()

with open(path.join(here, pkg_name, 'version.py')) as f:
    exec(f.read())

setup(
    name='datajoint-pipeline',
    version=__version__,
    description="Extracellular electrophysiology, Calcium Imaging, Fiber Photometry, DLC, Integrated behavior pipeline",
    long_description=long_description,
    author='DataJoint',
    author_email='info@datajoint.com',
    license='MIT',
    url='https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline',
    keywords='neuroscience datajoint ephys calcium imaging ',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=requirements,
    entry_points={
        'console_scripts': ['run_workflow=workflow.populate.process:cli'],
    }
)
