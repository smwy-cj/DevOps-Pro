FROM python:3.13-slim@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
WORKDIR /work
COPY main.c config.h Makefile test_app.py ./
RUN sed -i -e 's|http://deb.debian.org/debian-security|https://mirrors.tuna.tsinghua.edu.cn/debian-security|g' -e 's|http://deb.debian.org/debian|https://mirrors.tuna.tsinghua.edu.cn/debian|g' /etc/apt/sources.list.d/debian.sources
RUN apt-get -o Acquire::Retries=3 update && apt-get -o Acquire::Retries=3 install -y --no-install-recommends gcc make libc6-dev && rm -rf /var/lib/apt/lists/*
RUN make app
RUN python3 test_app.py
CMD ["./app"]
