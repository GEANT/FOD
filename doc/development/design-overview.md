
# Design Overview

## Application Overview

2 main components/programs/processes, both executing Python code, which is Django-based:

- Gunicorn # the HTTP front-end 
- Celeryd  # the back-end for actually performing NETCONF updates and SNMP statistics queries

(compare ./runfod.sh, the default start wrapper script)

as well as 

- a common database, 
  - either mysql or just an sqlite file
  - it contains the defined FlowSpec rules (active or inactive) + further model data
- redis as a task broker (for tasks + messages)

in between Gunicorn and Celeryd

## Python Code Overview

### Installation directories

- default installation directory proper: /srv/flowspy
- default installation directory for Python dependencies (via virtualenv): /srv/venv 

### Overview of directories and files in the repository 

#### Django Config

- Django settings: 
  - ./flowspy/settings.py 
  - ./flowspy/settings_local.py (the latter included from the former for separating non-host specific settings from host-specific ones in cases of multiple installations)

- ./flowspy/urls.py # Django urls config

#### Overview of directories and files with code

proper Python code, partly shared by gunicorn and celeryd components:

- ./flowspec/ 
  - for Gunicorn: views (for web UI), viewsets (for REST API), forms, validators; 
  - common to both, Gunicorn and Celeryd: models, serializers, tasks; 
  - snmpstats (for Celeryd), 
  - further: admin.py (customization of Django /admin interface), helper classes
- ./utils/    
  - mainly helper classes, 
  - but also proxy.py, which performs the actual NETCONF updates
- ./accounts/ 
- ./peers/
- ./poller/: sub system for live-status message support in web UI

- ./templates: Django web page templates


