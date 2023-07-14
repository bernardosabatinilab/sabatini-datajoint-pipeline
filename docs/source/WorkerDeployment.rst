Worker Deployment (WSL)
=======================

The following pipelines can be run via the docker containers: Calcium_Imaging_Worker, Spike_Sorting_Worker, and Standard_Worker.

For the DeepLabCut worker, we will run this from the provided `dlc notebook <https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline/blob/5d38f22f2caabf8cc91cb6fd18be2dbfaa632a2c/notebooks/dlc.ipynb>`_.

More on proper usage in the :doc:`How To` section.

An Important Note about worker deployment
#########################################

Once workers are up, they will begin populating the tables with data. Each worker will populate the following tables:

- *Standard_Worker: BehaviorIngestion, EphysRecording, CuratedClusting, WaveformSet, LFP, ScanInfo, MotionCorrection, Segmentation, Fluorescence, and Activity (all tables without large computational resources needed)

- *Spike_Sorting_Worker: Clustering table (runs Kilosort)
  
- *Calcium_Imaging_Worker: Processing table (in Imaging schema)

Workers will `continually` operate and will work if new data appears in your inbox directory. If no data is added, and data is not addes to LabBook, the workers will not do anything.

If there are any changes to the code, you will need to rebuild the images before running the workers again.

How to "Up" the workers
########################

We will be working in WSL/Ubuntu 20.04 CLI for this section.

Standard Worker
---------------

1. First, create a local ``.env`` file in ``./docker/standard_worker/`` based on the `standard example.env <https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline/blob/5d38f22f2caabf8cc91cb6fd18be2dbfaa632a2c/docker/standard_worker/example.env>`_.

You will need to fill in ``DJ_PASS`` (e.g. Datajoint Database Password), ``ROOT_DATA_DIR`` (e.g. local ``/Inbox`` data directory), ``PROCESSED_DATA_DIR`` (e.g. local ``/Outbox`` data directory).

2. Next, we will need to navigate to the ``./docker/standard_worker/dist/debian`` directory and build the worker image:

.. code-block:: bash

    cd ./docker/standard_worker/dist/debian

Now that we're in the right place, we will need to build the image:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard build --no-cache

The build should complete without any errors. If you receive errors please check your ``.env`` file and make sure you have the correct paths.

3. Now that the image is built, we can run the worker by running the following command:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard up -d

The worker should now be running in the background. You can check the status of the worker by running the following command:

.. code-block:: bash

    docker ps -a

If you wish to follow the container logs:

.. code-block:: bash

    docker logs -f [container-ID] -f 

4. To "down" the worker, run the following command:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-standard_worker.yaml -p sabatini-datajoint-pipeline_standard down


Spike Sorting Worker
--------------------

The spike sorting worker is a bit more complicated than the standard worker. This is because the spike sorting worker requires our MATLAB license to run and the GPU to run.
Please do not hesitate to contact the database manager for help with this section.

1. First, create a local ``.env`` file in ``./docker/spike_sorting_worker/`` based on the `spike sorting example.env <https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline/blob/5d38f22f2caabf8cc91cb6fd18be2dbfaa632a2c/docker/spike_sorting_local_worker/example.env>`_.

You will also need to edit the ``network.txt`` file to include our HMS MATLAB server. For both the ``.env`` and ``network.txt`` files, please contact the database manager for help.

2. We will then need to build the images. First, we will need to navigate to the ``./docker/spike_sorting_worker/dist/debian`` directory and build the worker image:

.. code-block:: bash

    cd ./docker/spike_sorting_worker/dist/debian

Now that we're in the right place, we will need to build the image:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-spike_sorting_worker.yaml -p sabatini-datajoint-pipeline_spike_sorting build --no-cache

Check that the build completed without any errors. If you receive errors please check your ``.env`` and ``network.txt`` file and make sure you have the correct information.

3. After the image has been built, we can run the worker by running the following command:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-spike_sorting_worker.yaml -p sabatini-datajoint-pipeline_spike_sorting up -d

The worker should now be running in the background. You can check the status of the worker by running the following command:

.. code-block:: bash

    docker ps -a

If you wish to follow the container logs:

.. code-block:: bash

    docker logs -f [container-ID] -f

4. Once you have finished using the worker, you can "down" the worker by running the following command:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-spike_sorting_worker.yaml -p sabatini-datajoint-pipeline_spike_sorting down


Calcium Imaging Worker
----------------------

The calcium imaging worker is similar to the standard worker. We will be running Suite2P for this worker and the paramaters can be set using the
provided `calcium_imaging notebook <https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline/blob/5d38f22f2caabf8cc91cb6fd18be2dbfaa632a2c/notebooks/calcium_imaging.ipynb>`_.

1. First, create a local ``.env`` file in ``./docker/calcium_imaging_worker/`` based on the `calcium example.env <https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline/blob/5d38f22f2caabf8cc91cb6fd18be2dbfaa632a2c/docker/calcium_imaging_worker/example.env>`_.

You will need to fill in ``DJ_PASS`` (e.g. Datajoint Database Password), ``ROOT_DATA_DIR`` (e.g. local ``/Inbox`` data directory), ``PROCESSED_DATA_DIR`` (e.g. local ``/Outbox`` data directory).

2. Next, we will need to build the images. First, we will need to navigate to the ``./docker/calcium_imaging_worker/dist/debian`` directory and build the worker image:

.. code-block:: bash

    cd ./docker/calcium_imaging_worker/dist/debian

Now that we're in the right place, we will need to build the image:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-calcium_imaging_worker.yaml -p sabatini-datajoint-pipeline_calcium_imaging build --no-cache

Check that the build completed without any errors. If you receive errors please check your ``.env`` file and make sure you have the correct paths.

3. After the image has been built, we can run the worker by running the following command:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-calcium_imaging_worker.yaml -p sabatini-datajoint-pipeline_calcium_imaging up -d

The worker should now be running in the background. You can check the status of the worker by running the following command:

.. code-block:: bash

    docker ps -a

If you wish to follow the container logs:

.. code-block:: bash

    docker logs -f [container-ID] -f

4. Once you have finished using the worker, you can "down" the worker by running the following command:

.. code-block:: bash

    docker compose --env-file=../../.env -f docker-compose-calcium_imaging_worker.yaml -p sabatini-datajoint-pipeline_calcium_imaging down