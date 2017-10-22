#!/bin/bash

set -eo pipefail

cd "$(dirname "$0")"
vagrant up
vagrant ssh-config > ssh_config
