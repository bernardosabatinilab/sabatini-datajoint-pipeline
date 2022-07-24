ARG PY_VER
ARG WORKER_BASE_HASH
FROM datajoint/djbase:py${PY_VER}-alpine-${WORKER_BASE_HASH}

USER root
RUN apk add openssh git vim
USER anaconda

ARG DEPLOY_KEY
COPY --chown=anaconda $DEPLOY_KEY $HOME/.ssh/id_ed25519
RUN chmod u=r,g-rwx,o-rwx $HOME/.ssh/id_ed25519

ARG REPO_OWNER
ARG REPO_NAME
WORKDIR $HOME
RUN ssh-keyscan github.com >> $HOME/.ssh/known_hosts && \
    git clone git@github.com:${REPO_OWNER}/${REPO_NAME}.git && \
    pip install ./${REPO_NAME}