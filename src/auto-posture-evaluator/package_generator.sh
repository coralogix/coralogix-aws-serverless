#!/bin/bash
FILE="${0}"
FILENAME=$(basename "${FILE}")
FOLDER=$(dirname "${FILE}")

rm deployment-package.zip
rm -R "${FOLDER}/package"
pip install --target "${FOLDER}/package" -r "${FOLDER}/requirements.txt"
cd "${FOLDER}/package" || exit 9
zip -r ../deployment-package.zip .
cd ..
zip -u deployment-package.zip ./*.py
zip -u deployment-package.zip testers/*
zip -u deployment-package.zip model/*
