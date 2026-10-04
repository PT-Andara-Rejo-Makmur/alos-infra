# syntax=docker/dockerfile:1.7
# Preserve the official PostgreSQL entrypoint while rebuilding its user-switch helper
# with a patched Go toolchain. The original gosu release still vendors an old Go runtime.
ARG POSTGRES_BASE_IMAGE=postgres:16-alpine@sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea
FROM --platform=$BUILDPLATFORM golang:1.27.1-alpine@sha256:8a5910f31396cd4d89662f56c68b3ae31d374308270a1c3bd96672ee5ed43414 AS gosu
ARG TARGETARCH
WORKDIR /src
RUN --mount=type=cache,target=/go/pkg/mod --mount=type=cache,target=/root/.cache/go-build \
    go mod init alos-gosu-build && go get github.com/tianon/gosu@1.19 && \
    CGO_ENABLED=0 GOOS=linux GOARCH=$TARGETARCH go build -trimpath -o /out/gosu github.com/tianon/gosu

FROM ${POSTGRES_BASE_IMAGE} AS vector
RUN apk add --no-cache build-base curl
WORKDIR /src
# Same pgvector version as the audited upstream pg16 image; checksum pins source bytes.
RUN curl --fail --location --retry 3 \
      https://codeload.github.com/pgvector/pgvector/tar.gz/f37c13f68b57d2c3472b2214fbcff699d6d34876 \
      --output vector.tar.gz && \
    echo '83d673c3b287cddbf3879f86215f043f2c2b56c69d37b2a77504910db1ed6e56  vector.tar.gz' | sha256sum -c - && \
    tar -xzf vector.tar.gz --strip-components=1 && \
    make -j2 OPTFLAGS="" with_llvm=no && \
    make install DESTDIR=/out with_llvm=no

FROM ${POSTGRES_BASE_IMAGE} AS runtime
COPY --from=gosu /out/gosu /usr/local/bin/gosu
COPY --from=vector /out/usr/local/lib/postgresql/vector.so /usr/local/lib/postgresql/vector.so
COPY --from=vector /out/usr/local/share/postgresql/extension/ /usr/local/share/postgresql/extension/
RUN apk upgrade --no-cache && \
    gosu --version && gosu nobody true
