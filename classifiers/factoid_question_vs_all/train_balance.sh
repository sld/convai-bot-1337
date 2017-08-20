#!/usr/bin/env bash

../fastText/fasttext supervised -input train_balance_shuf_tokenized.txt -output model -epoch 50 -wordNgrams 2
../fastText/fasttext test model.bin tests_balance_tokenized.txt
