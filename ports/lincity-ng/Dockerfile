# LinCity-NG 2.14 needs CMake 3.21, so bullseye is too old. libxml++ 5.0 is not packaged in
# bookworm, and the code needs fmt 11 (it includes fmt/base.h; its CMake asks for 9), so
# build.sh builds both from source as static libraries.
FROM --platform=linux/arm64 debian:bookworm-slim

RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        g++ make cmake ninja-build meson pkg-config xz-utils \
        libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
        libxml2-dev zlib1g-dev xsltproc gettext && \
    rm -rf /var/lib/apt/lists/*
