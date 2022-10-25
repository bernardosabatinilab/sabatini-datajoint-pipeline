#!/bin/bash
############################################
## Nvidia driver version is determined by GPU architecture(instance type) and
## CUDA toolkit version that you want to use

## 1. Find the Nvidia architecture for your instance type: https://towardsdatascience.com/choosing-the-right-gpu-for-deep-learning-on-aws-d69c157d8c86

## Based on the Nvidia architecture,
## 2. Find the Nvidia driver version and CUDA Toolkit version it supports: https://www.nvidia.com/Download/index.aspx?lang=en-us

## Based on the CUDA toolkit version you want to install,
## 3. Find the latest vesion of CUDA toolkit runfile url: https://developer.nvidia.com/cuda-downloads
## Or the archived versions of CUDA toolkit runfile url: https://developer.nvidia.com/cuda-toolkit-archive
############################################

## e.g g4dn instance with latest CUDA toolkit(11.7)
## sudo bash install_nvidia_driver.sh "515.48.07" "https://developer.download.nvidia.com/compute/cuda/11.7.0/local_installers/cuda_11.7.0_515.43.04_linux.run"

## e.g g4dn instance with matlab kilosort(depending on CUDA 11.0)
## sudo bash install_nvidia_driver.sh "450.191.01" "https://developer.download.nvidia.com/compute/cuda/11.0.3/local_installers/cuda_11.0.3_450.51.06_linux.run"

## e.g g4dn instance(depending on CUDA 11.2)
## sudo bash install_nvidia_driver.sh "460.106.00" "https://developer.download.nvidia.com/compute/cuda/11.2.2/local_installers/cuda_11.2.2_460.32.03_linux.run"

echo "INFO :: Install Nvidia Driver"
export DRIVER_VERSION=$1
export CUDA_TOOLKIT_RUNFILE_URL=$2
export BASE_URL=https://us.download.nvidia.com/tesla
wget -P /tmp $BASE_URL/$DRIVER_VERSION/NVIDIA-Linux-x86_64-$DRIVER_VERSION.run
sh /tmp/NVIDIA-Linux-x86_64-$DRIVER_VERSION.run -as
nvidia-smi

echo "INFO :: Install Nvidia CUDA Toolkit"
wget -P /tmp $CUDA_TOOLKIT_RUNFILE_URL
sh /tmp/cuda*linux.run --silent --toolkit
echo "PATH=/usr/local/cuda/bin:${PATH}" >> /root/.bashrc
echo "LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}" >> /root/.bashrc
echo "CUDA_CACHE_MAXSIZE=1073741824" >> /root/.bashrc
echo "PATH=/usr/local/cuda/bin:${PATH}" >> /home/ubuntu/.bashrc
echo "LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}" >> /home/ubuntu/.bashrc
echo "CUDA_CACHE_MAXSIZE=1073741824" >> /home/ubuntu/.bashrc
source /root/.bashrc
nvcc -V

echo "INFO :: Install Nvidia Container Runtime"
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg -q --yes --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt update
apt-get install -y nvidia-container-toolkit nvidia-docker2
systemctl restart docker
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
