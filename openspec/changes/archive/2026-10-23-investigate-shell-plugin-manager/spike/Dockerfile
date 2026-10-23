# Spike image for benchmarking shell setups.
# Build: docker build -t shell-spike:local spike/
# Ubuntu 24.04 because zsh-bench hangs with the `script` of util-linux 2.41 (Ubuntu 26.04).
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git zsh bash-completion sudo util-linux tmux gawk make \
        luajit lua5.4 xz-utils unzip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -s /usr/bin/zsh tester \
    && echo 'tester ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/tester

# Shell tools from mise (aqua/GitHub releases). Real binaries are linked into
# /usr/local/bin so mise shims do not add to the measured startup time.
ENV MISE_DATA_DIR=/opt/mise MISE_CONFIG_DIR=/opt/mise/config MISE_YES=1
RUN curl -fsSL https://mise.run | MISE_INSTALL_PATH=/usr/local/bin/mise sh \
    && mise use -g fzf eza fd zoxide starship atuin delta sheldon hyperfine \
    && for t in fzf eza fd zoxide starship atuin delta sheldon hyperfine; do \
         ln -sf "$(mise which "$t")" /usr/local/bin/"$t"; done \
    && chmod -R a+rX /opt/mise

# Benchmark tool and bash line editor
RUN git clone -q --depth 1 https://github.com/romkatv/zsh-bench /opt/zsh-bench \
    && curl -fsSL https://github.com/akinomyoga/ble.sh/releases/download/nightly/ble-nightly.tar.xz \
        | tar -xJ -C /opt \
    && mv /opt/ble-nightly /opt/blesh

# zsh-bench --isolation user runs setup via `sudo -Hu zsh-bench`; keep proxy settings.
RUN printf 'Defaults env_keep += "http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY"\n' \
      >/etc/sudoers.d/keep-proxy && chmod 440 /etc/sudoers.d/*[!E] && visudo -cq

USER tester
WORKDIR /home/tester
