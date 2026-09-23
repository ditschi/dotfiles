FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-venv \
        sudo \
        unzip \
        ansible-core \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL get.chezmoi.io | sh -s -- -b /usr/local/bin \
    && mkdir -p /usr/share/ansible/collections \
    && ansible-galaxy collection install ansible.posix \
        -p /usr/share/ansible/collections \
    && useradd --create-home --shell /bin/bash tester \
    && echo 'tester ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/tester \
    && chmod 0440 /etc/sudoers.d/tester

USER tester
ENV HOME=/home/tester
WORKDIR /dotfiles
