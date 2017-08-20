# Requirements

- Docker version 17.05.0-ce, build 89658be
- docker-compose version 1.13.0, build 1719ceb
- Min. 4 Gb RAM + Swap (4 Gb), recommended 8 Gb RAM
- Tested on Ubuntu 16.04

# Configure

`cp dialog_tracker/config.example.py dialog_tracker/config.py`

# How to run

1. `docker-compose -f docker-compose.yml -f convai.yml up -d --build`

# How to run tests for JSON API

1. `docker-compose -f docker-compose.yml -f json_api.yml up`
2. `python dialog_tracker/tests/test_main_api.py http://0.0.0.0:5000`
