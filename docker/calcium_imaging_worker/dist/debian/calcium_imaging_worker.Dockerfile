ARG PY_VER
ARG WORKER_BASE_HASH
FROM datajoint/djbase:py${PY_VER}-debian-${WORKER_BASE_HASH}

USER root
RUN apt-get update && \
    apt-get install -y ssh git vim nano

USER anaconda:anaconda

ARG REPO_OWNER
ARG REPO_NAME

WORKDIR $HOME

# Clone the workflow
RUN git clone -b main https://github.com/${REPO_OWNER}/${REPO_NAME}.git

# Install C++ compilers
RUN cp ./${REPO_NAME}/apt_requirements.txt /tmp/
RUN /entrypoint.sh echo "Installed dependencies."

# Install the workflow
RUN pip install ./${REPO_NAME}
