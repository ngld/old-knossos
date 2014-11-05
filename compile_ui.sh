#!/bin/bash

cd "$(dirname "$0")/ui"
for file in *.ui; do
  out="../knossos/ui/$(echo "$file" | sed 's#\.ui$#.py#')"
  make -s "$out"
done
