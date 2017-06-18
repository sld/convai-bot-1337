FROM python:3.6.1

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

EXPOSE 5000

CMD cd /src && python3 app.py --mode test --model_name example --vocab_size 100000 --size 256 --antilm 0.7 --beam_size 5
