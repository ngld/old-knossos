#!/bin/bash

echo "Copying files..."

[ -d tmp ] && rm -rf tmp
mkdir tmp

cd tmp
cp ../../../{hlp.png,hlp.ico,LICENSE} ../installer.nsi .
cp -r ../../dist/fs2mod-py data

echo "Creating archive..."
zip -r installer.zip *
mv installer.zip ..
cd ..

echo "Cleanup..."
rm -rf tmp
