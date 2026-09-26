"""Exercise the real Bash setup with isolated filesystem and command fixtures."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodespacesConfigurationTests(unittest.TestCase):
    def test_creation_runs_full_setup_and_waits_for_completion(self):
        config = json.loads(
            (REPO_ROOT / ".devcontainer" / "devcontainer.json").read_text()
        )
        self.assertEqual(
            config["postCreateCommand"],
            ["bash", "docs/codespaces/setup.sh", "--accept-cli-license"],
        )
        self.assertEqual(config["waitFor"], "postCreateCommand")
        self.assertEqual(
            config["remoteEnv"]["MCP_WORKSHOP_PYTHON"],
            "/opt/workshop-venv/bin/python",
        )
        for hook in ("onCreateCommand", "updateContentCommand"):
            self.assertNotIn(hook, config)


@unittest.skipUnless(
    sys.platform == "linux" and shutil.which("bash"),
    "Bash startup integration tests require Linux",
)
class CodespacesSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.venv = self.root / "venv"
        self.log = self.root / "commands.log"
        self.log.touch()
        self.script = self.root / "docs" / "codespaces" / "setup.sh"
        self.script.parent.mkdir(parents=True)

        self.executable("sudo", 'exec "$@"\n')
        self.executable("uname", 'echo "Linux x86_64"\n')
        self.executable("python", """
echo "python:$*" >> "$TEST_LOG"
if [[ "$*" == "-m pip install "* ]]; then
    [[ "${FAIL_STAGE:-}" != requirements ]] || exit 41
    touch "$TEST_ROOT/requirements-installed"
    cp "$TEST_TOOLS/foundry-local-install" "$VIRTUAL_ENV/bin/foundry-local-install"
elif [[ "$*" == scripts/verify_setup.py* || "$*" == scripts/prepare_vm.py ]]; then
    test -f "$TEST_ROOT/requirements-installed"
    test "$MCP_WORKSHOP_PYTHON" = "$VIRTUAL_ENV/bin/python"
    test "$(command -v python)" = "$VIRTUAL_ENV/bin/python"
    if [[ "$*" == scripts/prepare_vm.py ]]; then
        [[ "${FAIL_STAGE:-}" != model ]] || exit 43
    fi
fi
""")
        self.executable("base-python", """
echo "create-venv" >> "$TEST_LOG"
test "$1 $2" = "-m venv"
mkdir -p "$3/bin"
cp "$TEST_TOOLS/python" "$3/bin/python"
""")
        self.executable("foundry-local-install", """
echo "native-runtime" >> "$TEST_LOG"
[[ "${FAIL_STAGE:-}" != runtime ]] || exit 42
""")
        self.executable("curl", """
echo "download-cli" >> "$TEST_LOG"
while [[ "$1" != --output ]]; do shift; done
cp "$TEST_ROOT/cli.tar.gz" "$2"
""")

        release = self.root / "foundry-0.10.0-linux-x64" / "lib"
        release.mkdir(parents=True)
        for name in ("foundry", "foundrylocald"):
            binary = release / name
            binary.write_text('#!/bin/bash\necho "0.10.0"\n')
            binary.chmod(0o755)
        archive = self.root / "cli.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(release.parent, arcname=release.parent.name)
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()

        source = (REPO_ROOT / "docs" / "codespaces" / "setup.sh").read_text()
        # Redirect only external filesystem locations and the download digest.
        source = source.replace("/opt/workshop-venv", str(self.venv))
        source = source.replace("/usr/local/bin/python", str(self.tools / "base-python"))
        source = source.replace("/usr/local/bin/foundry", str(self.tools / "foundry"))
        source = source.replace(
            "bcad5aca68aafbe042d56d241e255fb4a8f90189d32a75f1657c3e06acedf323",
            checksum,
        )
        self.script.write_text(source)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{self.tools}:/usr/bin:/bin",
            "VIRTUAL_ENV": "/wrong-venv",
            "MCP_WORKSHOP_PYTHON": "/wrong-python",
            "TEST_ROOT": str(self.root),
            "TEST_LOG": str(self.log),
            "TEST_TOOLS": str(self.tools),
            "FAIL_STAGE": "",
        }

    def executable(self, name, body):
        path = self.tools / name
        path.write_text("#!/bin/bash\nset -eu\n" + body)
        path.chmod(0o755)

    def run_setup(self, *args):
        return subprocess.run(
            ["bash", str(self.script), *args],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=30,
        )

    def test_installs_requirements_cli_and_model_with_missing_environment(self):
        result = self.run_setup("--accept-cli-license")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        commands = self.log.read_text().splitlines()
        self.assertEqual(commands[0], "create-venv")
        self.assertIn(
            "python:-m pip install --no-input --disable-pip-version-check "
            "-r requirements-server.txt -c docs/codespaces/requirements-linux.lock",
            commands,
        )
        self.assertLess(
            commands.index("native-runtime"),
            commands.index("python:scripts/verify_setup.py --skip-model"),
        )
        self.assertLess(
            commands.index("download-cli"),
            commands.index("python:scripts/prepare_vm.py"),
        )
        self.assertEqual(commands[-1], "python:scripts/verify_setup.py")
        self.assertIn("Codespaces setup complete.", result.stdout)

        (self.root / "requirements-installed").unlink()
        self.log.write_text("")
        repeated = self.run_setup("--accept-cli-license")
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertNotIn("create-venv", self.log.read_text())
        self.assertNotIn("download-cli", self.log.read_text())
        self.assertTrue((self.root / "requirements-installed").exists())

    def test_invalid_cli_checksum_stops_before_model_preparation(self):
        (self.root / "cli.tar.gz").write_bytes(b"corrupted archive")
        result = self.run_setup("--accept-cli-license")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED", result.stdout)
        self.assertNotIn("python:scripts/prepare_vm.py", self.log.read_text())
        self.assertNotIn("Codespaces setup complete.", result.stdout)

    def test_failures_stop_setup_without_a_ready_message(self):
        for stage, code in (("requirements", 41), ("runtime", 42), ("model", 43)):
            with self.subTest(stage=stage):
                self.env["FAIL_STAGE"] = stage
                self.log.write_text("")
                result = self.run_setup("--accept-cli-license")
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertNotIn("Codespaces setup complete.", result.stdout)
                self.assertNotIn(
                    "python:scripts/verify_setup.py",
                    self.log.read_text().splitlines(),
                )
                if stage != "model":
                    self.assertNotIn("download-cli", self.log.read_text())

    def test_license_flag_is_required_before_installing(self):
        result = self.run_setup()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.log.read_text(), "")
