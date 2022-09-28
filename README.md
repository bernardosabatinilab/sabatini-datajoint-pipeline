### Installation

```
conda create -n dope -c conda-forge python=3.9 -y

conda activate dope

pip install -r requirements.txt 
pip install -e .  

```
### Worker Deployment using Docker
```

Pipeline Operation
1. New data is added into the specfied directory 
2. Using Labbook insert into Subject, Session, and SessionDirectory tables
    SessionDirectory should point to the root raw data directory
3. Once workers are docker composed up they will begin working on populating tables
    - Standard Worker will work on populating BehaviorIngestion, EphysRecording, CuratedClustering, WaveformSet, LFP, ScanInfo, MotionCorrection, Segmentation, Fluorescence, and Activity (all tables without large computational resources needed)
    - Spike Sorting Worker will work on populating Clustering table (runs kilosort)
    - Calcium Imaging Worker will work on populating Processing table (in Imaging schema)
    - DLC Worker will work on populating RecordingInfo and PoseEstimation tables
4. Workers will continually operate and will continue to do work if new data appears in the inbox folder, if no data is added, and data is not added to LabBook, the workers will not do anything until the data has been added.

Standard Worker Example (same for Calcium Imaging and DLC, just need cd to respective folder)
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

    docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard build --no-cache

    --no-cache flag included will rebuild image without using cache

After image has been built in order to bring up the container
    docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard up -d

    -d flag will start the container detached, in the background, and the current terminal window can continue to be used

To bring down the container
    docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard down

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

    docker compose --env-file=../../.env  -f docker-compose-spike_sorting_local_worker.yaml -p sabatini-datajoint-pipeline_spike build --no-cache

    --no-cache flag included will rebuild image without using cache

After image has been built in order to bring up the container
    docker compose --env-file=../../.env  -f docker-compose-spike_sorting_local_worker.yaml -p sabatini-datajoint-pipeline_spike up -d

    -d flag will start the container detached, in the background, and the current terminal window can continue to be used

To bring down the container
    docker compose --env-file=../../.env  -f docker-compose-spike_sorting_local_worker.yaml -p sabatini-datajoint-pipeline_spike down

```