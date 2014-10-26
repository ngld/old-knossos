#!/bin/bash

QRC_PATH="resources.qrc"
RCC_PATH="resources.rcc"

add_files() {
    while read path; do
        echo "<file>$path</file>"
    done >> "$QRC_PATH"
}

echo "Collecting resources..."

echo '<!DOCTYPE RCC><RCC version="1.0">' > "$QRC_PATH"
echo '<qresource>' >> "$QRC_PATH"

find ui -name '*.png' -or -name '*.jpg' -or -name '*.css' | add_files
find html -type f | add_files

echo '</qresource>' >> "$QRC_PATH"
echo '</RCC>' >> "$QRC_PATH"

echo "Packing resources..."
rcc -binary "$QRC_PATH" -o "$RCC_PATH"