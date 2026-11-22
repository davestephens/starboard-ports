# Bullseye's glibc 2.31 keeps the binary loadable on older handheld firmwares.
# Bullseye is end-of-life, so packages come from archive.debian.org.
FROM --platform=linux/arm64 debian:bullseye-slim

RUN printf '%s\n' \
        'deb http://archive.debian.org/debian bullseye main' \
        'deb http://archive.debian.org/debian-security bullseye-security main' \
        > /etc/apt/sources.list && \
    apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        gcc make libc6-dev libx11-dev libxext-dev binutils patch && \
    rm -rf /var/lib/apt/lists/*
