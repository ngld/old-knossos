#!/bin/bash

. "$(dirname "$0")/helpers.sh"

if [ "$1" = "compile_resources" ]; then
    compile_resources
    exit "$?"
elif [ -z "$1" ]; then
    echo "Usage: helpers.sh <action>"
    exit 2
else
    echo "Unknown action '$1'!"
    exit 1
fi