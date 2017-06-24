# Release scripts

This folder contains build scripts for every supported platform.

Each script uses Vagrant or Docker to launch the target OS in a VM or container. It then builds Knossos inside.
In general each folder contains a `prepare.sh` script which starts the VM / builds the container and a `build.sh` which runs the actual build.

The detailed requirements are:
* FreeBSD: [Vagrant][vg] and [Packer][pack]; The `prepare.sh` script uses Packer to build the FreeBSD VM image using a script from GitHub.
* macOS: [Vagrant][vg]; The VM image is downloaded from Atlas.
* Ubuntu: [Docker][dock]; The container is downloaded from Docker Hub.
* Windows: [Vagrant][vg] and [Packer][pack]; You have to clone https://github.com/ngld/packer-windows and build the `windows_7.json` file with Packer. Afterwards add it to Vagrant using `vagrant box add --name=windows_10 <path to your .box file>`.

[vg]: https://www.vagrantup.com/
[pack]: https://www.packer.io/
[dock]: https://www.docker.com/
