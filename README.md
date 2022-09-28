### Installation

```
conda create -n dope -c conda-forge python=3.9 -y

conda activate dope

pip install -r requirements.txt 
pip install -e .  

```
### Worker Deployment using Docker
```
Standard Worker Example
To adapt to other workers, follow same convention, just cd to the respective folder
First, 

    cd ./docker/standard_worker/

Create a local .env file based on the template build.env
Will need to fill in MATLAB_HOSTID, MATLAB_FILE_KEY, DJ_PASS, ROOT_DATA_DIR, PROCESSED_DATA_DIR
MATLAB_HOSTID - MAC Address supplied to Mathworks as HostID associated with license.
MATLAB_FILE_KEY - Mathworks provided file key associated with installation.
MATLAB_LICENSE_PATH - Local File Path location for MATLAB_LICENSE (.lic file)

Next, 

    cd /docker/standard_worker/dist/debian/

Run Docker Commands to build/up worker images

    docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard build --no-cache

    --no-cache flag included will rebuild image without using cache

After image has been built in order to bring up the container
    docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard up -d

To bring down the container
    docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard down

    docker ps -a --> command to view all open containers, lists container-IDs
    docker logs [container-ID] -f --> command to view container logs (-f follows output)

Additional useful docker commands for docker memory management
    docker image prune
    docker volume prune
    docker system prune

```