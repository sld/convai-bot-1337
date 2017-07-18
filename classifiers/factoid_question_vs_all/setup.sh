#!/usr/bin/env bash

cat ../squad/questions.txt ../cornell\ movie-dialogs\ corpus/only_lines.txt > data.txt
gshuf data.txt > data_shuf.txt
head -n 39231 data_shuf.txt > test.txt
tail -n 353080 data_shuf.txt > train.txt

