# Host configs for the CI and the Docker integration tests, apart from the real hosts
# in machine/hosts/. The test containers use the file name as host name and set
# MACHINE_HOSTS_DIR=tests/hosts, so `machine` reads these files (do not rename).
#   ci-container.yml   — dotfiles only
#   ci-rpi-zero.yml    — ansible+apt slim (Pi Zero, hardware set by MACHINE_HARDWARE)
#   ci-home-laptop.yml — ansible+apt GNOME (L13 Yoga mirror, MACHINE_HARDWARE=laptop)
