FROM python:3.7
LABEL maintainer="dgarros@gmail.com"

RUN mkdir /source
WORKDIR /source
USER root

COPY . /source
RUN pip install -e /source/arcapi-master
RUN pip install -r /source/requirements.txt

RUN python setup.py develop


ENTRYPOINT ["/usr/local/bin/metric-collector"]
