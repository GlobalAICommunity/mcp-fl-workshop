# Build and distribute the Codespaces image

This guide is for facilitators. The [learner guide](README.md) explains how to
complete the lab after the image has been published and these files are
available on a repository branch.

The image is an environment, not a snapshot of someone's running Codespace.
It deliberately excludes credentials, learner files, CLI binaries, model
weights, and runtime caches.

## What is distributed

The Linux `amd64` image packages Python 3.12, FastMCP 4.0.0, Foundry Local
Python SDK 2.0.1 and its native runtime, and the browser dependencies. The base
image is pinned by digest, and Python dependencies are constrained by the
Linux-specific [lock file](requirements-linux.lock).

The [Foundry Local license](https://github.com/microsoft/foundry-local/blob/main/LICENSE)
licenses the SDK under MIT but prohibits sharing or publishing the CLI.
Consequently, [setup.sh](setup.sh) obtains CLI preview 0.10.0 directly from
Microsoft only after each user explicitly accepts its terms. Model weights
are also downloaded per user, under their own license. Do not publish a
`docker commit` of a container after running setup.

| Component | Image contents |
|---|---|
| Base | Microsoft Python dev container, Debian 12, Python 3.12 |
| Python environment | `/opt/workshop-venv`, selected through `PATH` |
| Dependency record | `/opt/workshop/requirements-linux.lock` |
| Workshop source | Cloned by Codespaces, not copied into the image |
| CLI and CPU model | Downloaded separately in the user's Codespace |
| Platform | `linux/amd64`; this is not a multi-architecture image |

### Published release

Published on 2026-09-26 through
[workflow run 36227366613](https://github.com/GlobalAICommunity/mcp-fl-workshop/actions/runs/36227366613).
The [GHCR package](https://github.com/orgs/GlobalAICommunity/packages/container/package/mcp-fl-workshop)
is **private** and linked to this repository. Grant Codespaces/learner access
before distributing the lab link.

```text
Tag: ghcr.io/globalaicommunity/mcp-fl-workshop:codespaces-20260926
Digest: ghcr.io/globalaicommunity/mcp-fl-workshop@sha256:7dcf83a3117092b7afabdfc5c9abf00f7a8808cec64816949f0835401a5e3390
Source: 9591715 (image build and dependency files)
```

The Codespaces configuration pins this digest rather than the mutable tag.
The release passed 25 deterministic tests and Linux setup, native CPU
tool-calling, terminal-agent, and browser API checks.

The Dockerfile removes the base image's unused Yarn APT source because its
signing key no longer validates. Debian repository signature verification
remains enabled. The workshop does not require Yarn.

## Build a new release

Use Docker on Linux, or Docker Desktop configured for Linux containers. The
commands below use Bash. Run them from the repository root and allow several
GB of free disk space for the image and build cache.

Use a new tag when changing the environment. A tag can be overwritten;
a **digest** identifies the exact published image. Preserve the digest for
repeatable workshop delivery.

```bash
IMAGE=ghcr.io/globalaicommunity/mcp-fl-workshop:codespaces-20260926
docker build --platform linux/amd64 \
  --build-arg SOURCE_REVISION="$(git rev-parse HEAD)" \
  --file docs/codespaces/Dockerfile \
  --tag "$IMAGE" .
```

[Dockerfile.dockerignore](Dockerfile.dockerignore) allows only the required
dependency manifests, Docker build files, and repository license into the
build context. Never replace it with `COPY . .`, which could package `.env`
files, caches, or credentials.

The image installs the direct requirements from
[requirements-server.txt](../../requirements-server.txt), constrained by the
Linux lock. Do not reuse [requirements-lock.txt](../../requirements-lock.txt):
it is the accepted Windows dependency closure.

## Accept the image before publishing

Test the actual image as its non-root `vscode` user, not the host Python
environment. Package installation alone does not prove native model loading
or a valid tool call.

Create a disposable validation container with the repository mounted. Review
the CLI and model licenses first. This test downloads them into the container's
writable layer, **not into the image that will be pushed**.

```bash
docker run --name mcp-workshop-acceptance \
  --mount "type=bind,source=$PWD,target=/workspaces/mcp-fl-workshop" \
  --workdir /workspaces/mcp-fl-workshop \
  "$IMAGE" bash -c \
  'bash docs/codespaces/setup.sh --accept-cli-license &&
   python -m unittest discover -s tests -v &&
   python scripts/validate_content.py'
```

Success requires the full readiness message, a `get_weather(Pune)` tool call,
passing deterministic tests, and valid content links. The setup-only
`--skip-model` check is insufficient.

Keep networking enabled: the Linux SDK needs catalog access to resolve aliases
even with cached weights. An isolated `--network none` acceptance run could not
resolve `qwen2.5-1.5b`; this image is for the online Codespaces lab.

Also complete the learner's terminal agent, browser weather question, and
approval exercise. Keep port 7932 private in Codespaces. To test through local
Docker, publish it only on loopback with `-p 127.0.0.1:7932:7932`.

After inspecting the result, remove only the named disposable container:

```bash
docker rm mcp-workshop-acceptance
```

Do not commit or push this container: its writable layer contains downloaded
CLI binaries. Only push the image built from the Dockerfile.

## Publish to GHCR

GitHub Container Registry (**GHCR**) stores the image independently of the
source repository. Publishing requires write access to the organization
package namespace and an authenticated GitHub CLI account with `write:packages`.

Use password input through a pipe, never a token in a Dockerfile, image build
argument, Git remote URL, or checked-in configuration. Organization SSO or
package-creation policy may require administrator approval.

### Publish with GitHub Actions

The repository includes
[Publish Codespaces image](../../.github/workflows/codespaces-image.yml),
which builds and publishes with the repository's `GITHUB_TOKEN`. It requests
`packages: write` and never installs the CLI or downloads model weights.
Its automated checks cover packages, protocol behavior, unit tests and links;
the full model acceptance described above remains a release prerequisite.

The initial release also triggers on image-related pushes to
`leestott-foundry-local-codespace`. After merging, use **Actions > Publish
Codespaces image > Run workflow**. Set a new tag in the workflow and
configuration when intentionally releasing a different environment.

### Publish from your terminal

If the organization allows your account to create packages, the equivalent
terminal flow is:

```bash
gh auth refresh -h github.com -s write:packages
docker_config="$(mktemp -d)"
gh auth token | docker --config "$docker_config" login ghcr.io \
  --username "$(gh api user --jq .login)" --password-stdin
docker --config "$docker_config" push "$IMAGE"
docker --config "$docker_config" logout ghcr.io
rm -f "$docker_config/config.json"
rmdir "$docker_config"
```

If publishing fails, still run the logout and cleanup commands. A successful
push prints a `sha256:...` digest. Record the full `ghcr.io/...@sha256:...`
reference and use it in [devcontainer.json](devcontainer.json) to prevent
an accidental tag update from changing the learner environment.

### Package access

New packages are normally private. Publishing does not automatically make the
image available to every workshop attendee.

Open the organization's package settings, link the package to
`GlobalAICommunity/mcp-fl-workshop`, and grant that repository access for
Codespaces. Grant intended users read access as required. Only change package
visibility to Public if the organization approves public distribution.

Confirm access using a learner account, not just the publisher's account.
Private-registry setup is described in
[GitHub's Codespaces image access documentation](https://docs.github.com/en/codespaces/reference/allowing-your-codespace-to-access-a-private-registry).

## Create Codespaces from this image

Push these files to the branch learners will use. The published image does
not contain the repository checkout, so the image and that branch are both
needed. The learner command explicitly selects
`docs/codespaces/devcontainer.json`.

To make this the repository's default Codespaces configuration later, add a
root `.devcontainer/devcontainer.json` with the same image/settings in a
separate change. Keeping the configuration here avoids changing the existing
Windows workshop by default.

For faster workspace creation, consider
[Codespaces prebuilds](https://docs.github.com/en/codespaces/prebuilding-your-codespaces/about-github-codespaces-prebuilds).
Prebuild only the redistributable environment: **do not** move the CLI setup
into `onCreateCommand`, `updateContentCommand`, or an image build layer.
The current `postCreateCommand` checks packages without downloading the CLI
or model.

## Export an archive instead

The same built image can be distributed as a Docker archive to people who
cannot pull from GHCR. An archive contains the base and dependency layers,
not a learner's mounted source files or downloaded CLI/model caches.

Export only the original built image. Recipients still need this repository
and must run the per-user setup after accepting the relevant licenses.

```bash
docker image save "$IMAGE" | gzip > mcp-fl-workshop-linux-amd64.tar.gz
sha256sum mcp-fl-workshop-linux-amd64.tar.gz
```

On the recipient's Linux Docker host:

```bash
gunzip -c mcp-fl-workshop-linux-amd64.tar.gz | docker image load
```

GitHub Codespaces cannot boot directly from a tar archive. Publish it to a
registry that Codespaces can access, or use it locally with Docker/Dev
Containers. Image and registry storage, Codespaces compute, and prebuilds
can all incur charges.
