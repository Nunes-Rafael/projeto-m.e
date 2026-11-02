"""Check repository files without printing possible credential values."""

from pathlib import Path
import re
import subprocess


PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_or_openrouter_key": re.compile(r"\bsk-(?:proj-|or-v1-)?[A-Za-z0-9_-]{32,}\b"),
    "github_token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{50,})\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}


def check() -> int:
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    ).decode().split("\0")
    findings = set()
    for name in filter(None, paths):
        path = Path(name)
        if not path.is_file():
            continue
        if (path.name == ".env" or path.name.startswith(".env.")
                or path.suffix in {".pem", ".key"}) and path.name != ".env.example":
            findings.add(f"{name}: sensitive filename")
        raw = path.read_bytes()
        if b"\0" in raw:
            continue
        for line_number, line in enumerate(raw.decode(errors="replace").splitlines(), 1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.add(f"{name}:{line_number}: {kind}")
    for finding in sorted(findings):
        print(f"Potential credential: {finding}")
    if not findings:
        print("No sensitive filenames or supported credential patterns found.")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(check())
