#!/bin/bash

until curl --fail -v -I "http://localhost:5000"
do
  echo 'Waiting for the Flask listener to start ...'
  sleep 1
done
echo 'Flask listener started.'

PID="/tmp/exabgp.pid" exabgp /opt/exabgp/live/exabgp.conf
