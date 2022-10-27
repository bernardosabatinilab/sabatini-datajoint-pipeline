#!/bin/bash
export DRIVER_VERSION=$1
export BASE_URL=https://us.download.nvidia.com/tesla
curl -fSsl -O $BASE_URL/$DRIVER_VERSION/NVIDIA-Linux-x86_64-$DRIVER_VERSION.run
sh NVIDIA-Linux-x86_64-$DRIVER_VERSION.run --uninstall
