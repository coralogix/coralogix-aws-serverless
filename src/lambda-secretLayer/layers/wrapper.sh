#!/bin/bash

node /opt/wrapper.js
#cat /tmp/envVars

source /tmp/envVars

exec "$@"