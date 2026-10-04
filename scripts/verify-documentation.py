"""Check Markdown file links in the five sibling ALOS repositories without network access."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPOSITORIES = ("alos-web", "alos-backend", "genesis-ai", "alos-contracts", "alos-infra")
LINK = re.compile(r"\[[^\]\n]+\]\((<[^>\n]+>|[^)\n]+)\)")
REFERENCE = re.compile(r"^\s{0,3}\[[^\]\n]+\]:\s*(<[^>\n]+>|\S+)", re.MULTILINE)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def documentation_files(repo: Path) -> list[Path]:
    paths: set[str] = set()
    for arguments in (("ls-files", "-z"), ("ls-files", "--others", "--exclude-standard", "-z")):
        result = subprocess.run(["git", "-C", str(repo), *arguments], check=True,
                                capture_output=True, text=True)
        paths.update(result.stdout.split("\0"))
    return sorted(repo / name for name in paths if name.lower().endswith(".md") and (repo / name).is_file())


def visible_markdown(text: str) -> str:
    lines: list[str] = []
    marker = ""
    for line in text.splitlines():
        fence = FENCE.match(line)
        if fence:
            candidate = fence.group(1)
            if not marker:
                marker = candidate
            elif candidate[0] == marker[0] and len(candidate) >= len(marker):
                marker = ""
            lines.append("")
        else:
            lines.append("" if marker else line)
    return "\n".join(lines)


def local_target(source: Path, raw: str, workspace: Path) -> Path | None:
    target = raw.strip()
    if target.startswith("<"):
        target = target[1:target.index(">")]
    else:
        target = re.sub(r'\s+["\'][^"\']*["\']\s*$', "", target)
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        parts = parsed.path.strip("/").split("/")
        if (parsed.hostname == "github.com" and len(parts) >= 5
                and parts[0].lower() == "pt-andara-rejo-makmur"
                and parts[1] in REPOSITORIES and parts[2] in {"blob", "tree"}
                and parts[3] == "development"):
            return workspace.joinpath(parts[1], *[unquote(part) for part in parts[4:]])
        return None
    if not parsed.path:
        return None
    return source.parent / unquote(parsed.path)


def path_problem(target: Path) -> str | None:
    # Check spelling component by component so Windows does not conceal links
    # that would fail on Linux CI or on GitHub after a case-only typo.
    current = Path(target.anchor)
    for component in target.parts[1:]:
        if component == ".":
            continue
        if component == "..":
            current = current.parent
            continue
        if not current.is_dir():
            return "missing target"
        names = {child.name for child in current.iterdir()}
        if component not in names:
            return "wrong case" if component.lower() in {name.lower() for name in names} else "missing target"
        current /= component
    return None if current.exists() else "missing target"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    failures: list[str] = []
    documents = links = 0
    for name in REPOSITORIES:
        repo = workspace / name
        if not (repo / ".git").exists():
            failures.append(f"{name}: missing sibling Git checkout")
            continue
        for source in documentation_files(repo):
            documents += 1
            text = visible_markdown(source.read_text(encoding="utf-8-sig"))
            for match in (*LINK.finditer(text), *REFERENCE.finditer(text)):
                target = local_target(source, match.group(1), workspace)
                if target is None:
                    continue
                links += 1
                problem = path_problem(target)
                if problem:
                    line = text[:match.start()].count("\n") + 1
                    failures.append(f"{source.relative_to(workspace).as_posix()}:{line}: {problem}: {match.group(1)}")
    for failure in failures:
        print(failure)
    print(f"Markdown: {documents} files, {links} file links, {len(failures)} failures")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
