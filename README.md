# ConvAI bot#1337

Skill-based Conversational Agent that took 1st place at 2017 NIPS Conversational Intelligence Challenge (http://convai.io).

We still update our Conversational Agent and the latest version could be found in master branch.

Here is submitted to **ConvAI Finals version** of the Agent (on 12th November): https://github.com/sld/convai-bot-1337/tree/032d5f6f5cc127bb56d29f0f0c6bbc0487f98316

# Abstract

We present bot#1337: a dialog system developed for the 1st NIPS Conversational Intelligence Challenge 2017 (ConvAI). The aim of the competition was to implement a bot capable of conversing with humans based on a given passage of text. To enable conversation, we implemented a set of skills for our bot, including chit-chat, topic detection, text summarization, question answering and question generation. The system has been trained in a supervised setting using a dialogue manager to select an appropriate skill for generating a response. The latter allows a developer to focus on the skill implementation rather than the finite state machine based dialog manager. The proposed system bot#1337 won the competition with an average dialogue quality score of 2.78 out of 5 given by human evaluators. Source code and trained models for the bot#1337 are available on GitHub.

# Getting Started

For brief overview the bot#1337 take a look on next resources:

- [COLING 2018 Paper](http://aclweb.org/anthology/C18-1312)
- [one-page abstract](https://www.researchgate.net/publication/322037222_Skill-based_Conversational_Agent)
- [presentation](https://www.researchgate.net/publication/322037067_Skill-based_Conversational_Agent)

# Telegram Bot demo and JSON API

- Conversational agent demonstration is accessible as a Telegram bot: https://t.me/ConvAI1337Bot. 
- Also we have public JSON API that documented at https://github.com/sld/convai-bot-1337/wiki/Api-Documentation.

## Prerequisites

- Docker version 17.05.0-ce+
- docker-compose version 1.13.0+
- Min. 4 Gb RAM + Swap (4 Gb), recommended 8 Gb RAM
- 2 Gb hard drive space
- Tested on Ubuntu 16.04

## Installing

Download and put trained models to folders:

```
./setup.sh
```

Build containers:

```
docker-compose -f docker-compose.yml -f telegram.yml build
```

Setup config.py, do not forget to put TELEGRAM token:

```
cp dialog_tracker/config.example.py dialog_tracker/config.py
```

dialog_tracker/config.py should look like this:

```
WAIT_TIME = 15
WAIT_TOO_LONG = 60
version = "17 (24.12.2017)"
telegram_token = "your telegram token"
```

## Running the bot

This command will run the telegram bot with your telegram token:

```
docker-compose -f docker-compose.yml -f telegram.yml up
```

# Running the tests

Run the bot by using json api server:

```
docker-compose -f docker-compose.yml -f json_api.yml up
```

Run the tests:

```
python dialog_tracker/tests/test_json_api.py http://0.0.0.0:5000
```

# Contributing

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.

# Authors

- Idris Yusupov (http://github.com/sld)
- Yurii Kuratov (http://github.com/yurakuratov)

# License

This project is licensed under the GPLv3 License - see the LICENSE file for details.

# Other

Fork of this bot in TOP-3 (infinity team) of [DeepHack Chat](http://deephack.me/chat) hackathon http://deephack.me/leaderboard_hack.


