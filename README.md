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

cd /docker/standard_worker/

create a local .env file based on the template build.env
Will need to fill in MATLAB_HOSTID, MATLAB_FILE_KEY, DJ_PASS, ROOT_DATA_DIR, PROCESSED_DATA_DIR

Next, 

cd /docker/standard_worker/dist/debian/

Run Docker Commands to build/up worker images

docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard build --no-cache

--no-cache flag included will rebuild image without using cache

After image has been built

docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard up -d

docker compose --env-file=../../.env  -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard logs

docker ps -a --> command to view all open containers, lists container-IDs
docker logs [container-ID] -f --> command to view container logs (-f follows output)

Can access the container using this command

docker exec -it [container-ID] bash
Inside the container, can run ipython
In ipython shell we can run


Additional useful docker commands for docker memory management
docker image prune
docker volume prune
docker system prune
```