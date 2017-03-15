#!/usr/bin/env bash
## Copyright 2015 Knossos authors, see NOTICE file
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##     http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.

. "$(dirname "$0")/helpers.sh"

if [ "$1" = "compile_resources" ]; then
    compile_resources
    exit "$?"
elif [ "$1" = "gen_qrc" ]; then
    gen_qrc
    exit "$?"
elif [ -z "$1" ]; then
    echo "Usage: helpers.sh <action>"
    exit 2
else
    echo "Unknown action '$1'!"
    exit 1
fi
