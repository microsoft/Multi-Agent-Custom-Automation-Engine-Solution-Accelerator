FROM mcr.microsoft.com/devcontainers/python:3.11-bullseye

# Route npm/corepack traffic (used during devcontainer feature installation,
# e.g. ghcr.io/devcontainers/features/node) through the internal package feed
# proxy, since the public npmjs.org registry is blocked/unreachable on this
# network and causes feature install failures (ERR_SSL_SSL/TLS_ALERT_HANDSHAKE_FAILURE).
ENV NPM_CONFIG_REGISTRY=https://packagefeedproxy.microsoft.io/npm/

# Remove Yarn repository to avoid GPG key expiration issue
RUN rm -f /etc/apt/sources.list.d/yarn.list