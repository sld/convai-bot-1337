# Requirements

- Docker version 17.05.0-ce, build 89658be
- docker-compose version 1.13.0, build 1719ceb
- Min. 4 Gb RAM + Swap (4 Gb), recommended 8 Gb RAM
- Tested on Ubuntu 16.04

- GloVe can be downloaded here: https://nlp.stanford.edu/projects/glove/

# Configure

`cp dialog_tracker/config.example.py dialog_tracker/config.py`

# How to run

1. `docker-compose -f docker-compose.yml -f convai.yml up -d --build`

# How to run tests for JSON API

1. `docker-compose -f docker-compose.yml -f json_api.yml up`
2. `python dialog_tracker/tests/test_main_api.py http://0.0.0.0:5000`


# Data files

```
<TITLE> <FOLDER> <NAME>
MESSAGE_CLASSIFIER_MODEL dialog_tracker/data/ model_all_labels.ftz
QUESTION_GENERATION question_generation/data/ model.t7
OS_Chit_Chat opennmt_chitchat/data/ CPU_epoch5_14.62.t7
Summary opennmt_summarization/models/ textsum_epoch7_14.69_release.t7
FB_Chit_Chat fbnews_chitchat/data/ model_epoch18_93.23_release.t7
intent_classifier intent_classifier/data/ glove.6B.100d.txt
```
