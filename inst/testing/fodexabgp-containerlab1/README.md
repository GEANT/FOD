
= HowTo run FoD-exabgp container and freertr container in containerlab

* 0   prerequiste: have containerlab installed
      - https://containerlab.dev/
* 1   clone FoD repo 
      - $ git clone https://github.com/GEANT/FOD/tree/feature/exabgp_support2 && cd FOD
* 2.1 build FoD-exabgp container
      - in top dir of cloned FoD repo: 
      - $ docker build -f inst/testing/fodexabgp-containerlab1/Dockerfile -t fodexabgp-containerlab1 . 
* 2.2 run containerlab
      - for running:     $ containerlab deploy  --topo ./inst/testing/fodexabgp-containerlab1/005-rare-hello-fod/rtr005.clab.yml
      - (for inspecting: $ containerlab inspect --topo ./inst/testing/fodexabgp-containerlab1/005-rare-hello-fod/rtr005.clab.yml)
      - (for deleting:   $ containerlab delete  --topo ./inst/testing/fodexabgp-containerlab1/005-rare-hello-fod/rtr005.clab.yml)
* 2.3 in parallel to 2.2
      - ./inst/testing/fodexabgp-containerlab1/docker_8000_redir


