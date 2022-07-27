ARG PY_VER
ARG DIST
FROM datajoint/djbase:py${PY_VER}-${DIST}

USER root
RUN apt update && \
    apt-get install -y ssh git

USER anaconda:anaconda
ARG DEPLOY_KEY
COPY --chown=anaconda --chmod=700 $DEPLOY_KEY $HOME/.ssh/sciops_deploy.ssh

ARG REPO_OWNER
ARG REPO_NAME

WORKDIR $HOME

# Install Facemap
RUN git clone https://github.com/MouseLand/facemap.git
RUN pip install ./facemap

# Clone the workflow
RUN ssh-keyscan github.com >> ~/.ssh/known_hosts && \
    GIT_SSH_COMMAND="ssh -i $HOME/.ssh/sciops_deploy.ssh" \
    git clone git@github.com:${REPO_OWNER}/${REPO_NAME}.git

# Install C++ compilers for CaImAn
RUN cp ./${REPO_NAME}/apt_requirements.txt /tmp/
RUN /entrypoint.sh echo "Installed dependencies."

# Install the workflow
RUN GIT_SSH_COMMAND="ssh -i $HOME/.ssh/sciops_deploy.ssh" \
    pip install ./${REPO_NAME}
