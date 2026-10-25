# Caching apt proxy for local integration test runs (see tests/integration/conftest.py).
# Many test containers can share it at once; a shared /var/cache/apt/archives cannot
# (apt locks it and a second container fails right away).
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends apt-cacher-ng \
    && rm -rf /var/lib/apt/lists/* \
    && install -d -o apt-cacher-ng -g apt-cacher-ng /run/apt-cacher-ng

USER apt-cacher-ng
EXPOSE 3142
CMD ["/usr/sbin/apt-cacher-ng", "-c", "/etc/apt-cacher-ng", "ForeGround=1"]
