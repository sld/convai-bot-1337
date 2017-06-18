FROM python:3.6.1

WORKDIR /src

RUN apt-get update && apt-get install -y libzmq3-dev

COPY requirements.txt /tmp/requirements-dt.txt
COPY from_question_generation/requirements.txt /tmp/requirements-fqg.txt
RUN pip install -r /tmp/requirements-dt.txt
RUN pip install -r /tmp/requirements-fqg.txt

CMD python main.py
