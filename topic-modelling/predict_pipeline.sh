#!/bin/bash

UUID=$(hexdump -n 4 -v -e '/1 "%02X"' /dev/urandom)
FILENAME="$1"
cat "$FILENAME" | python tokenizing.py > "/tmp/tm-$UUID"
./predict.sh "/tmp/tm-$UUID" "/tmp/pred-tm-$UUID"
echo "/tmp/pred-tm-$UUID"
