import re
import subprocess
from pathlib import Path

from .providers import Artifact


SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*[^\s]+")


class PolicyViolation(Exception):
    pass


class WorkspacePolicy:
    allowed_test_commands = (("python", "-m", "pytest"),)

    def validate_path(self, root: Path, relative: str) -> bool:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            return False
        return not Path(relative).is_absolute() and ".git" not in Path(relative).parts

    def validate_artifacts(self, root: Path, artifacts: list[Artifact]) -> None:
        if len(artifacts) > 20:
            raise PolicyViolation("Artifact count exceeds policy")
        for artifact in artifacts:
            if not self.validate_path(root, artifact.path):
                raise PolicyViolation(f"Unsafe artifact path: {artifact.path}")
            if len(artifact.content) > 100_000:
                raise PolicyViolation(f"Artifact too large: {artifact.path}")
            if SECRET_PATTERN.search(artifact.content):
                raise PolicyViolation(f"Potential secret in artifact: {artifact.path}")

    def apply(self, root: Path, artifacts: list[Artifact]) -> None:
        self.validate_artifacts(root, artifacts)
        root.mkdir(parents=True, exist_ok=True)
        for artifact in artifacts:
            target = root / artifact.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(artifact.content, encoding="utf-8")

    def run_tests(self, root: Path, timeout: int) -> dict:
        command = ("python", "-m", "pytest", "-q")
        if command[:3] not in self.allowed_test_commands:
            raise PolicyViolation("Test command is not allowlisted")
        result = subprocess.run(
            command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False,
            env={"PATH": str(Path(__file__).resolve().parents[1] / ".venv" / "bin")},
        )
        output = SECRET_PATTERN.sub("[REDACTED]", (result.stdout + result.stderr)[-4000:])
        return {"passed": result.returncode == 0, "exit_code": result.returncode, "output": output}

