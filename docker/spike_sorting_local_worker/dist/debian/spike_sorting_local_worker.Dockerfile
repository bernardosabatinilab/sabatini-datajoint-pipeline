FROM datajoint/matlab:R2022a-GUI

USER root
## system level dependencies
RUN apt-get update
COPY ./apt_requirements.txt /tmp/apt_requirements.txt
RUN xargs apt-get install -y < /tmp/apt_requirements.txt

## NVIDIA driver is managed by nvidia-container-toolkit and nvidia-docker-2
## https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#setting-up-nvidia-container-toolkit

## Downgrade gcc/g++ for cuda
RUN apt-get install -y gcc-9 g++-9 && \
    rm /usr/bin/gcc && \
    rm /usr/bin/g++ && \
    ln -s /usr/bin/gcc-9 /usr/bin/gcc && \
    ln -s /usr/bin/g++-9 /usr/bin/g++

## CUDA Toolkit
RUN wget -P /tmp/ http://developer.download.nvidia.com/compute/cuda/11.0.2/local_installers/cuda_11.0.2_450.51.05_linux.run
RUN cd /tmp && bash cuda*.run --silent --toolkit
ENV PATH /usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH /usr/local/cuda-11.0/lib64:${LD_LIBRARY_PATH}
ENV CUDA_CACHE_MAXSIZE 1073741824

## MATLAB Python API
RUN cd /home/muser/.MATLAB/extern/engines/python && python setup.py install
RUN apt-get install -y tk
ENV PATH /home/muser/.MATLAB/bin:${PATH}
## Fix: libcrypto.so.1.1: version `OPENSSL_1_1_1' not found
WORKDIR /tmp
RUN wget https://www.openssl.org/source/openssl-1.1.1g.tar.gz
RUN tar -zxf openssl-1.1.1g.tar.gz
WORKDIR /tmp/openssl-1.1.1g
RUN ./config && make && make install
RUN mv /usr/bin/openssl /tmp/ && ln -s /usr/local/bin/openssl /usr/bin/openssl
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}
RUN rm /usr/lib/x86_64-linux-gnu/libcrypto.so.1.1
WORKDIR /
## Fix: libstdc++.so.6: version `CXXABI_1.3.11' not found
## This fix will cause: mexGPU build failure(Undefined spikedetector3) commented for now
#RUN cp /home/muser/.MATLAB/sys/os/glnxa64/libstdc++.so.6.0.25 /usr/lib/x86_64-linux-gnu/
#RUN rm /usr/lib/x86_64-linux-gnu/libstdc++.so.6
#RUN ln -s /usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.25 /usr/lib/x86_64-linux-gnu/libstdc++.so.6

## Mounted Data Volume Permission
RUN groupadd ubuntu --gid 1000
RUN usermod -aG ubuntu muser

RUN groupadd anaconda --gid 999
RUN usermod -aG anaconda muser

## mkdir for everything
USER muser:anaconda
RUN mkdir /home/muser/neuropixel
WORKDIR /home/muser/neuropixel

## CatGT
RUN wget -P /tmp/ http://billkarsh.github.io/SpikeGLX/Support/CatGTLnxApp.zip
RUN unzip /tmp/CatGTLnxApp.zip
RUN cd ./CatGT-linux && bash install.sh
ENV catGTPath=/home/muser/neuropixel/CatGT-linux

## TPrime
RUN wget -P /tmp/ http://billkarsh.github.io/SpikeGLX/Support/TPrimeLnxApp.zip
RUN unzip /tmp/TPrimeLnxApp.zip
RUN cd ./TPrime-linux && bash install.sh
ENV tPrime_path=/home/muser/neuropixel/TPrime-linux

## C_Waves
RUN wget -P /tmp/ http://billkarsh.github.io/SpikeGLX/Support/C_WavesLnxApp.zip
RUN unzip /tmp/C_WavesLnxApp.zip
RUN cd ./C_Waves-linux && bash install.sh
ENV cWaves_path=/home/muser/neuropixel/C_Waves-linux

## SpikeBandMedianSubtraction
RUN wget -P /tmp/ https://github.com/AllenInstitute/ecephys_spike_sorting/files/4821847/SpikeBandMedianSubtraction.zip
RUN unzip /tmp/SpikeBandMedianSubtraction.zip
ENV median_subtraction_executable=/home/muser/neuropixel/SpikeBandMedianSubtraction

## KiloSort
## 3.0
#RUN git clone https://github.com/MouseLand/Kilosort.git Kilosort-3.0
RUN git clone https://github.com/jenniferColonell/Kilosort2 Kilosort-3.0
RUN cp /home/muser/neuropixel/Kilosort-3.0/CUDA/mexGPUall.m /home/muser/neuropixel/Kilosort-3.0/CUDA/mexGPUall_determ.m && \
   sed -i 's/-DENABLE_STABLEMODE mexMPnu8.cu/-DENSURE_DETERM -DENABLE_STABLEMODE mexMPnu8.cu/' /home/muser/neuropixel/Kilosort-3.0/CUDA/mexGPUall_determ.m
## 2.5
RUN wget -P /tmp/ https://github.com/jenniferColonell/Kilosort2/archive/refs/tags/v2.5.zip
RUN unzip /tmp/v2.5.zip
RUN mv Kilosort2-2.5 Kilosort-2.5
RUN cp /home/muser/neuropixel/Kilosort-2.5/CUDA/mexGPUall.m /home/muser/neuropixel/Kilosort-2.5/CUDA/mexGPUall_determ.m && \
   sed -i 's/-DENABLE_STABLEMODE mexMPnu8.cu/-DENSURE_DETERM -DENABLE_STABLEMODE mexMPnu8.cu/' /home/muser/neuropixel/Kilosort-2.5/CUDA/mexGPUall_determ.m
## 2.0
RUN wget -P /tmp/ https://github.com/jenniferColonell/Kilosort2/archive/refs/tags/v2.0.zip
RUN unzip /tmp/v2.0.zip
RUN mv Kilosort2-2.0 Kilosort-2.0
RUN cp /home/muser/neuropixel/Kilosort-2.0/CUDA/mexGPUall.m /home/muser/neuropixel/Kilosort-2.0/CUDA/mexGPUall_determ.m && \
   sed -i 's/-DENABLE_STABLEMODE mexMPnu8.cu/-DENSURE_DETERM -DENABLE_STABLEMODE mexMPnu8.cu/' /home/muser/neuropixel/Kilosort-2.0/CUDA/mexGPUall_determ.m


## mexGPU build require cuda and matlab in the temp container
## cuda can use --gpu(docker run) or runtime: nvidia(docker-compose)
## matlab has to make sure this temp container has the matlab license and the mac address registered on the license
## the only difficulty is to set mac_address for the temp container
## TODO - find out how to set mac_address while docker-compose build

WORKDIR /home/muser/neuropixel

## pykilosort
#RUN git clone https://github.com/MouseLand/pykilosort.git
RUN git clone https://github.com/Yambottle/pykilosort.git
RUN pip install cupy-cuda110
## pip install packages that requires cuda build, will be enable in docker run --gpu or docker-compose.yaml runtime: nvidia
RUN sed -i 's/cupy/cupy-cuda110==10.0.0/' /home/muser/neuropixel/pykilosort/requirements.txt && \
   pip install -r /home/muser/neuropixel/pykilosort/requirements.txt && \
   pip install phylib pyqtgraph pyqt5 && \
   pip install /home/muser/neuropixel/pykilosort/

## npy_matlab
RUN git clone https://github.com/kwikteam/npy-matlab.git

ARG CACHE_AT=$(date)
## ecephys_spike_sorting
RUN git clone https://github.com/ttngu207/ecephys_spike_sorting.git
#RUN pip install ./ecephys_spike_sorting/
#RUN pip install argschema==1.* marshmallow==2.*
ENV ecephys_directory=/home/muser/neuropixel/ecephys_spike_sorting/ecephys_spike_sorting
ENV median_subtraction_repo=/home/muser/neuropixel/ecephys_spike_sorting/ecephys_spike_sorting/modules/median_subtraction/SpikeBandMedianSubtraction

## Workflow Array Ephys

# Clone the workflow
RUN git clone -b main https://github.com/${REPO_OWNER}/${REPO_NAME}.git

# Install the workflow
RUN pip install --upgrade pip && \
    pip install --use-deprecated=legacy-resolver ./${REPO_NAME}