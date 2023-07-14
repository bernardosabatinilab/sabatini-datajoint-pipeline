Installation
============

The sabatini-datajoint pipeline is run through Docker containers and requires access to our AWS server. To get started, you will need to install Docker and get access to our AWS server
by reaching out to HMS IT. 

Requirements
############

* Docker. Please follow the instructions for your operating system `here <https://docs.docker.com/get-docker/>`_.
  
* Anacoda or Miniconda. Please follow the `instructions for your operating system <https://docs.conda.io/projects/conda/en/latest/user-guide/install/>`_.
  
* If using Windows, we will also need a local installation of python. Please follow `these instructions <https://www.python.org/downloads/windows/>`_.
  
* If using Windows, you will need to `install the Windows Subsystem for Linux (WSL) and Ubuntu 20.04 <https://docs.microsoft.com/en-us/windows/wsl/install-win10>`_.
  
* For the DeepLabCut, Calcium Imaging, and Spike Sorting Worker, we will need a `CUDA compatible NVIDIA GPU <https://developer.nvidia.com/cuda-gpus>`_ and `drivers <https://developer.nvidia.com/cuda-toolkit-archive>`_ and `Microsoft C++ Build Tools <https://visualstudio.microsoft.com/visual-cpp-build-tools/>`_ for Windows.


Installation
############

1. After you have successfully installed Docker, Anaconda, and WSL, we will set up our conda environment.
   
.. literalinclude:: ../helpers/create_env.txt

You will need to activate the environment with ``conda activate sabatini-datajoint`` and navigate into the ``sabatini-datajoint`` directory.

**Optional**: If you are planning to make changes to the code, you may want to install the package in editable mode. This will allow you to make changes to the code and have them reflected in the Docker containers.
You can do this by running ``pip install -e .`` 

1. Create a copy of `.example_dj_local_conf.yaml <https://github.com/bernardosabatinilab/sabatini-datajoint-pipeline/blob/5d38f22f2caabf8cc91cb6fd18be2dbfaa632a2c/.example_dj_local_config.json>`_ 
and rename it to `dj_local_conf.yaml`. 

3. Fill in the appropriate information for the ``database.host``, ``database.user``, and ``database.password`` fields.

4. You may then launch ``jupyter notebook`` and navigate to the ``notebooks`` directory to run the notebooks. Please make sure to set your kernel to ``sabatini-datajoint``.
   

WSL Configuration for NVIDIA GPU Support
########################################

1. Using Windows Powershell, install Ubuntu in WSL by running

.. code-block:: bash

    wsl --install -d Ubuntu-20.04

2. Set Ubuntu to use WSL2
   
.. code-block:: bash

    wsl --set-version Ubuntu-20.04 2

3. Confirm that your local Ubuntu version is integrated in the docker app (Settings > Resources > WSL Integration)

4. Install `CUDA in WSL <https://docs.nvidia.com/cuda/wsl-user-guide/index.html#getting-started-with-cuda-on-wsl>`_.

5. Configure your WSL-Ubuntu as a root user in order to use the Docker containers. Run the following in Windows Powershell:
   
.. code-block:: bash

    ubuntu2004 config --default-user root

6. Install the NVIDIA Container Toolkit in WSL using the following specifications: Linux OS, x86_64 architecture, Ubuntu distribution, 20.04 release, version 2.0, runfile (local).
Then, follow the `base installer instructions <https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=WSL-Ubuntu&target_version=2.0&target_type=runfile_local>`_.

7. Confirm that /etc/docker/daemon.json contains a runtime component pointing to the correct nvidia-container-runtime path.
This is updated by default in Ubuntu, but may need to be manually set in Windows.

8. Restart Docker Desktop and WSL-Ubuntu.

9. Update all .env paths using the WSL-Ubuntu path. For example, ``/mnt/c/Users/username/..``.


  
