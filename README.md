# Sabatini Lab - DataJoint Workflow Setup Instructions

# For more information, please visit our [documentation page](https://sabatini-datajoint-pipeline.readthedocs.io/en/latest/index.html).

## Quick Installation Instructions

```
conda create -n sabatini-datajoint -c conda-forge python=3.9 -y

conda activate sabatini-datajoint
conda install graphviz python-graphviz pydotplus ipykernel ipywidgets nb_conda_kernels jupyterlab

git clone https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline

Navigate into cloned repository
cd sabatini-datajoint-pipeline/

pip install -r requirements.txt 
pip install -e . 
- This step of pip installing in -editable mode, must be rerun if you want to test with local changes

Create a copy of .example_dj_local_config.json, rename it to dj_local_conf.json and fill in database user/host/password credentials

Launch Jupyter Notebook/Lab and set kernel to the sabatini-datajoint conda environment
```

## Expected Directory Structure

```
Your data ``/Inbox`` directory structure will need to be set up like the following: 

| dlc_projects
|       └── PROJECT_PATH
| Subject1
| ├── Session1
|    ├── Imaging
|     ├── scan0
|        ├── 00001.tif
|        ├── 00002.tif
|        └── ...
|    ├── Photometry
|       ├── timeseries*.mat; data*.mat; .tdt
|       └── .toml
|    ├── Behavior
|       ├── .toml
|       └── .parquet, .csv
|    ├── Ephys
|       └── .bin, .lf, .meta
|    ├── dlc_behavior_videos
|       └── .avi
|
| ├── Session2
|   └── ...

Note that the ``Subject`` is the top level directory, and all other data types are nested. You do not need to have all data types for each session.
For DLC related projects, the ``dlc_projects`` directory is expected to be in the Inbox directory *not* the subject directory.

```
