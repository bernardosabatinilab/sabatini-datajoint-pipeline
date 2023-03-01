ARG PY_VER
ARG WORKER_BASE_HASH
FROM datajoint/djbase:py${PY_VER}-debian-${WORKER_BASE_HASH}

USER root
RUN apt-get update && \
    apt-get install -y ssh git build-essential vim nano

RUN conda install -c conda-forge cudatoolkit=11.6 cudnn=8.3.2
ENV CUDA_CACHE_MAXSIZE=1073741824

USER anaconda:anaconda

ARG REPO_OWNER
ARG REPO_NAME
WORKDIR $HOME

# Install Deeplabcut
RUN git clone https://github.com/DeepLabCut/DeepLabCut.git
RUN pip install ./DeepLabCut

# Clone the workflow
RUN git clone -b main https://github.com/${REPO_OWNER}/${REPO_NAME}.git

# Install C++ compilers for CaImAn
RUN cp ./${REPO_NAME}/apt_requirements.txt /tmp/
RUN /entrypoint.sh echo "Installed dependencies."

# Install the workflow
RUN pip install ./${REPO_NAME}

ENV LD_LIBRARY_PATH="/lib:/opt/conda/lib"