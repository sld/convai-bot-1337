# Requirements

- Docker version 17.05.0-ce, build 89658be
- docker-compose version 1.13.0, build 1719ceb
- Min. 4 Gb RAM + Swap (4 Gb), recommended 8 Gb RAM
- Tested on Ubuntu 16.04

# How to run

`docker-compose -f docker-compose.yml -f convai.yml up -d --build`


# How to

1. wget https://s3.eu-central-1.amazonaws.com/convai/convai-bot-1337-ver6.tar.gz
2. tar -zxvf convai-bot-1337-ver6.tar.gz
3. cd convai-bot-1337-to-send/
4. docker-compose -f docker-compose.yml -f convai.yml up -d --build
