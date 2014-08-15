#!/bin/bash

cd "$(dirname "$0")/ui"
for file in *.ui; do
  echo "$file..."
  
  out="$(echo "$file" | sed 's#\.ui$#.py#')"
  pyside-uic -o "$out" "$file"
  sed -i 's#from PySide import#from lib.qt import#' "$out"
done
