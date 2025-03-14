#!/bin/bash

FILE=$1
CLIENTS=$2

echo "Generating compose file for $CLIENTS clients modifying $FILE"
python3 generator.py $FILE $CLIENTS

if [ $? -eq 0 ]; then
    echo "Compose file generated successfully"
else
    echo "Error generating compose file"
fi