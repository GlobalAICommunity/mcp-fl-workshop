FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm@sha256:7876580dc67fd460fd962f004cbeb480027e9bbc0657096f1087db11f9eaff39

ARG SOURCE_REVISION
LABEL org.opencontainers.image.title="MCP workshop for GitHub Codespaces" \
      org.opencontainers.image.description="Linux CPU environment for the MCP workshop; CLI and models are installed separately by each user." \
      org.opencontainers.image.source="https://github.com/GlobalAICommunity/mcp-fl-workshop" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"

USER root
RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 libicu72 libssl3 \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/workshop-venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}" \
    MCP_WORKSHOP_PYTHON="${VIRTUAL_ENV}/bin/python" \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements-server.txt /opt/workshop/requirements-server.txt
COPY docs/codespaces/requirements-linux.lock /opt/workshop/requirements-linux.lock
COPY LICENSE /opt/workshop/LICENSE
RUN python -m venv "${VIRTUAL_ENV}" \
    && python -m pip install --no-cache-dir \
        -r /opt/workshop/requirements-server.txt \
        -c /opt/workshop/requirements-linux.lock \
    && foundry-local-install \
    && python -m pip check

USER vscode
CMD ["sleep", "infinity"]
