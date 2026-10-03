# Supported versions: UBUNTU_VERSIONS in tests/integration/conftest.py
ARG UBUNTU_VERSION=26.04
FROM ubuntu:${UBUNTU_VERSION}
ARG UBUNTU_VERSION

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        python3 \
        python3-venv \
        zsh \
        sudo \
        unzip \
        ansible-core \
    # 25.10+ default to sudo-rs; classic sudo stays available as sudo.ws
    && case "$UBUNTU_VERSION" in 24.04) ;; *) apt-get install -y --no-install-recommends sudo-rs ;; esac \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL get.chezmoi.io | sh -s -- -b /usr/local/bin \
    && curl -LsSf https://astral.sh/uv/install.sh | env UV_UNMANAGED_INSTALL=/usr/local/bin sh \
    && mkdir -p /usr/share/ansible/collections \
    && ansible-galaxy collection install ansible.posix \
        -p /usr/share/ansible/collections \
    && useradd --create-home --shell /bin/bash tester \
    && echo 'tester ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/tester \
    && chmod 0440 /etc/sudoers.d/tester \
    # Second user whose sudo asks for a password (test credential, containers only)
    && useradd --create-home --shell /bin/bash --groups sudo pwtester \
    && echo 'pwtester:machine-test-password' | chpasswd \
    && echo 'machine-test-password' >/home/pwtester/.become-password \
    && chown pwtester:pwtester /home/pwtester/.become-password \
    && chmod 0600 /home/pwtester/.become-password

USER tester
ENV HOME=/home/tester
WORKDIR /dotfiles
