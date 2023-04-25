### Installation and setting up local environment to access database

```bash
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

### Testing setup instructions

```python
- Rerun editable installation of codebase to make sure that most updated local code is run
    pip install -e .

- Navigate inside sabatini-datajoint-pipeline/ while in sabatini-datajoint conda environment
- Launch ipython (type ipython into terminal) after (cd sabatini-datajoint-pipeline/)
or 
- Navigate to jupyter notebook, configured with updated conda environment

Next, import the necessary modules from the pipeline:
- Run line [from workflow.pipeline import *]
- Now that variables have been defined, you should see the database schemas present, can verify by displaying the session.Session() table. 
- Define the key of interest: If you are testing insertion of a new subject with a new type of data format you can do this by inserting into subject.Subject(), session.Session(), and session.SessionDirectory() tables. To obtain the session_key, you can run
    
    session_key = (session.Session() & 'subject="subject_name").fetch1("KEY")
    photometry_key = (photometry.FiberPhotometry.key_source & session_key) 

- Using this key of interest, you can move to testing the make function of the table that you wish to modify. For example, to test any updates to the photometry.FiberPhotometry() function, you can manually rerun the .populate() function with the key specified. If there are errors in the code and you want to debug to see where the issue is, you should set the python debugger to be active (%pdb on), that way you can step into the make method and rerun the lines of code previous to that which has errored in order to determine what the issue is. 
- This testing can be performed without the python debugger if that is easier. To do this, within the ipython/jupyter environment(where you are running the testing), you need to import the specific imports that are necessary to run that function (i.e. in the case of photometry all the imports defined at the top of photometry.py). Then you can manually run line-by-line each line of the specific .make() method that you are modifying in order to see the data you are working with, and verify that the implemented changes work as intended.

    photometry.FiberPhotometry.populate(key)
    photometry.FiberPhotometry.make(photometry.FiberPhotometry(), key)
```

### Windows Nvidia GPU Configuration (using Windows Subsystem for Linux (WSL))

```bash
1. Update OS to allow for developer options: Windows 10 2022 Update | Version 22H2
2. Install WSL using powershell
3. Confirm Ubuntu exists in WSL installation by running

    wsl --install -d Ubuntu-20.04

4. Set Ubuntu to use WSL2 

    wsl --set-version Ubuntu-20.04 2

5. Make sure that your version of Ubuntu is integrated in the docker app (Settings > Resources > WSL integration)
6. Install CUDA in WSL: https://docs.nvidia.com/cuda/wsl-user-guide/index.html#getting-started-with-cuda-on-wsl
7. WSL-Ubuntu must be configured to be a root user in order to use Docker. Run in powershell: 

    ubuntu2004 config --default-user root

8. Install Cuda toolkit in WSL - Use Linux OS, x86_64 architecture, WSL-Ubuntu Distribution, Version 2.0, runfile(local). Then, follow the base installer instructions.

    https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=WSL-Ubuntu&target_version=2.0&target_type=runfile_local

9. Confirm that /etc/docker/daemon.json contains a runtime component pointing to the correct nvidia-container-runtime path. (This is updated by default in Ubuntu, but needs to be manually set in Windows)
10. Update all .env paths with WSL Ubuntu path format. For example: /mnt/c/Users/Janet/...
```

### Worker Deployment using Docker Container (in WSL)

```bash

Pipeline Operation
1. New data is added into the specfied directory 
2. Using Labbook insert into Subject, Session, and SessionDirectory tables
    SessionDirectory should point to the root raw data directory
3. Once workers are docker composed up they will begin working on populating tables
    - Standard Worker will work on populating BehaviorIngestion, EphysRecording, CuratedClustering, WaveformSet, LFP, ScanInfo, MotionCorrection, Segmentation, Fluorescence, and Activity 
    (all tables without large computational resources needed)
    - Spike Sorting Worker will work on populating Clustering table (runs kilosort)
    - Calcium Imaging Worker will work on populating Processing table (in Imaging schema)
4. For DLC operation, activate conda environment and run the DLC notebook to process new videos     
    through trained models.    
4. Workers will continually operate and will continue to do work if new data appears in the inbox folder.
    If no data is added, and data is not added to LabBook, the workers will not do anything until the data has been added.

Standard Worker Example (same for Calcium Imaging and DLC, just need cd to respective folder)

Within WSL: 

First, 

    cd ./docker/standard_worker/

Create a local .env file based on the template example.env
Will need to fill in DJ_PASS, ROOT_DATA_DIR, PROCESSED_DATA_DIR
    DJ_PASS - Datajoint Database Password
    ROOT_DATA_DIR - Local Inbox Data Directory 
    PROCESSED_DATA_DIR - Local Outbox Data Directory

Next, 

    cd ./docker/standard_worker/dist/debian/

Run Docker Commands to build/up worker images

    docker compose --env-file=../../.env -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard build --no-cache

    --no-cache flag included will rebuild image without using cache

After image has been built in order to bring up the container
    docker compose --env-file=../../.env -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard up -d

    -d flag will start the container detached, in the background, and the current terminal window can continue to be used

To bring down the container
    docker compose --env-file=../../.env -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard down

    docker ps -a --> command to view all open containers, lists container-IDs
    docker logs [container-ID] -f --> command to view container logs (-f follows output)

Additional useful docker commands for docker memory management
    docker image prune 
        Removes all dangling images. If -a is specified, will also remove all images not referenced by any container.
    docker volume prune
        Removes all unused local volumes. Unused local volumes are those which are not referenced by any containers.
    docker system prune
        Removes all unused containers, networks, images (both dangling and unreferenced), and optionally, volumes.


Spike Sorting Worker Example

Within WSL:

First,

    cd ./docker/spike_sorting_local_worker/

Create a local .env file based on the template example.env
Will need to fill in MATLAB_HOSTID, MATLAB_FILE_KEY, DJ_PASS, ROOT_DATA_DIR, PROCESSED_DATA_DIR
    MATLAB_HOSTID - MAC Address supplied to Mathworks as HostID associated with license.
    MATLAB_FILE_KEY - Mathworks provided file key associated with installation.
    MATLAB_LICENSE_PATH - Local File Path location for MATLAB_LICENSE (.lic file)
    DJ_PASS - DataJoint Database Password
    ROOT_DATA_DIR - Local Inbox Data Directory 
    PROCESSED_DATA_DIR - Local Outbox Data Directory

Next, 

    cd ./docker/spike_sorting_local_worker/dist/debian/

Run Docker Commands to build/up worker images

    docker compose --env-file=../../.env -f docker-compose-spike_sorting_local_worker.yaml -p sabatini-datajoint-pipeline_spike build --no-cache

    --no-cache flag included will rebuild image without using cache

After image has been built in order to bring up the container
    docker compose --env-file=../../.env -f docker-compose-spike_sorting_local_worker.yaml -p sabatini-datajoint-pipeline_spike up -d

    -d flag will start the container detached, in the background, and the current terminal window can continue to be used

To bring down the container
    docker compose --env-file=../../.env -f docker-compose-spike_sorting_local_worker.yaml -p sabatini-datajoint-pipeline_spike down

```
