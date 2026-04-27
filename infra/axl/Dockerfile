# Multi-stage Dockerfile for the Gensyn AXL `node` binary.
# Builds on Linux (avoids the Go 1.25.5 + gVisor + openssl native-Windows pain).
# Each Lethe agent runs its own copy of this image with its own keypair + config.

FROM golang:1.25.5-bookworm AS build
WORKDIR /src
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG AXL_REPO=https://github.com/gensyn-ai/axl.git
ARG AXL_REF=main
RUN git clone "$AXL_REPO" axl && cd axl && git checkout "$AXL_REF"

WORKDIR /src/axl

# Try every reasonable output location, then fall back to a direct go build.
# Whichever path wins, the final binary lands at exactly /out/node.
RUN mkdir -p /out && \
    set -eux; \
    if make build 2>/dev/null; then \
      if [ -x ./node ];          then cp -f ./node          /out/node; \
      elif [ -x ./bin/node ];    then cp -f ./bin/node      /out/node; \
      elif [ -x ./cmd/node/node ]; then cp -f ./cmd/node/node /out/node; \
      else (cd cmd/node && go build -o /out/node .); \
      fi; \
    else \
      (cd cmd/node && go build -o /out/node .); \
    fi; \
    test -x /out/node


FROM debian:bookworm-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl socat \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /out/node /usr/local/bin/node

# AXL binds its HTTP API to 127.0.0.1:9002 inside the container regardless
# of config. We use socat to expose it on the container's external port 9100
# so Docker port-mapping can reach it from the host.
# (Can't bind socat to 0.0.0.0:9002 — overlaps with AXL's 127.0.0.1:9002.)
RUN cat > /usr/local/bin/start.sh <<'SH'
#!/bin/sh
set -e
CONFIG="${1:-/config/alpha.json}"
echo "[start.sh] launching AXL with config $CONFIG"
/usr/local/bin/node -config "$CONFIG" &
NODE_PID=$!
# Wait briefly for AXL to bind 127.0.0.1:9002
sleep 1
echo "[start.sh] starting socat 0.0.0.0:9100 -> 127.0.0.1:9002"
socat TCP-LISTEN:9100,fork,reuseaddr TCP:127.0.0.1:9002 &
SOCAT_PID=$!
wait $NODE_PID $SOCAT_PID
SH
RUN chmod +x /usr/local/bin/start.sh

WORKDIR /axl
EXPOSE 9100 7000

# Default — each compose service overrides with its own config path.
CMD ["/usr/local/bin/start.sh", "/config/alpha.json"]