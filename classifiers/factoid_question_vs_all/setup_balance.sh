#!/usr/bin/env bash

gshuf -n 87599 comments_with_label.txt > comments_87k.txt
gshuf -n 87599 ../squad/questions.txt > questions87k.txt
gshuf -n 87599 ../cornell\ movie-dialogs\ corpus/only_lines.txt > movies87k.txt
gshuf -n 87599 squad_answers_with_label.txt > squad_answers87k.txt


head -n 599 comments_87k.txt > test_balance.txt
head -n 599 questions87k.txt >> test_balance.txt
head -n 599 movies87k.txt >> test_balance.txt
head -n 599 squad_answers87k.txt >> test_balance.txt

tail -n 87000 comments_87k.txt > train_balance.txt
tail -n 87000 questions87k.txt >> train_balance.txt
tail -n 87000 movies87k.txt >> train_balance.txt
tail -n 87000 squad_answers87k.txt >> train_balance.txt

gshuf train_balance.txt > train_balance_shuf.txt
python my-tokenize.py train_balance_shuf.txt > train_balance_shuf_tokenized.txt
python my-tokenize.py test_balance.txt > tests_balance_tokenized.txt
