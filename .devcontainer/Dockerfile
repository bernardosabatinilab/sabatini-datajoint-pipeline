FROM python:3.9-slim@sha256:5f0192a4f58a6ce99f732fe05e3b3d00f12ae62e183886bca3ebe3d202686c7f 

ENV PATH /usr/local/bin:$PATH
ENV PYTHON_VERSION 3.9.17

RUN \
    adduser --system --disabled-password --shell /bin/bash vscode && \
    # install docker
    apt-get update && \
    apt-get install ca-certificates curl gnupg lsb-release -y && \
    mkdir -m 0755 -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y && \
    usermod -aG docker vscode && \
    apt-get clean

RUN \
    # dev setup
    apt update && \
    apt-get install sudo git gcc bash-completion graphviz default-mysql-client -y && \
    usermod -aG sudo vscode && \
    echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers && \
    pip install --no-cache-dir --upgrade black pip && \
    echo '. /etc/bash_completion' >> /home/vscode/.bashrc && \
    echo 'export PS1="\[\e[32;1m\]\u\[\e[m\]@\[\e[34;1m\]\H\[\e[m\]:\[\e[33;1m\]\w\[\e[m\]$ "' >> /home/vscode/.bashrc && \
    apt-get clean

# COPY ./requirements.txt /tmp/

# RUN \
#     # tutorial dependencies
#     pip install --no-cache-dir black faker ipykernel && \
#     pip install --no-cache-dir -r /tmp/requirements.txt && \
#     rm /tmp/requirements.txt

# ENV DJ_HOST fakeservices.datajoint.io
# ENV DJ_USER root
# ENV DJ_PASS simple

USER vscode
CMD bash -c "sudo rm /var/run/docker.pid; sudo dockerd"