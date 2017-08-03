#!/bin/bash

set -eo pipefail
cd "$(dirname "$0")"

exec xfreerdp /u:vagrant /p:vagrant /v:127.0.0.1:3389 /size:1024x768 /gfx:rfx /rfx
