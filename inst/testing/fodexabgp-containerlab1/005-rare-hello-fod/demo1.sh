#!/bin/sh

# to be run from FoD main dir

set -x
cd ./inst/testing/fodexabgp-containerlab1/005-rare-hello-fod/ && exec ./containerlab-fod-freertr.sh "$@"
