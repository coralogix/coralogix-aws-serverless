#!/bin/bash

node_version=$(node -e "console.log(process.version)")

if [[ $node_version == v16.* || $node_version == v14.* ]]; then
    node /opt/wrapper16.js
    #cat /tmp/envVars
    
    source /tmp/envVars
else
    node /opt/wrapper18.js
    #cat /tmp/envVars
    
    source /tmp/envVars
fi

exec "$@"
