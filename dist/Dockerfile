FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV DOT_SAGE=/home/ctf/.sage
ENV FLAG=flag{dummy}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        sagemath \
        socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 ctf

WORKDIR /app
COPY generate.sage /app/dist/generate.sage

RUN sage -preparse /app/dist/generate.sage \
    && rm -rf /tmp/.sage \
    && mkdir -p /home/ctf/.sage \
    && chown -R ctf:ctf /home/ctf/.sage \
    && chmod 0555 /app /app/dist \
    && chmod 0444 /app/dist/generate.sage /app/dist/generate.sage.py

USER ctf
EXPOSE 1337

CMD ["socat", "-T", "10", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:sage /app/dist/generate.sage.py,stderr"]
