#!/usr/bin/env python3
"""Install the text-only skill explicitly, without overwriting user files.

Python 3.10+, stdlib. No shell, network, registry or agent configuration changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path

NAME = "multi-agent-planning-agent-skill"
ROOT_FILES = (
    "SKILL.md", "README.md", "LICENSE", "SECURITY.md", "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md", "CHANGELOG.md", "AGENTS.md", "CLAUDE.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
)
RESOURCE_DIRS = ("references", "scripts", "assets", "examples", ".github/ISSUE_TEMPLATE")
RESOURCE_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml"}


def is_link(path: Path) -> bool:
    """Reject symlinks and Windows reparse points, including 3.10 junctions."""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def check_source_path(source: Path, path: Path) -> None:
    current = source
    for part in path.relative_to(source).parts:
        current = current / part
        if is_link(current):
            raise ValueError(f"links não são distribuídos: {current.relative_to(source)}")


def manifest(source: Path) -> list[Path]:
    """Enumerate only documented, regular package files; reject symlinks."""
    files = []
    for name in ROOT_FILES:
        path = source / name
        check_source_path(source, path)
        if not path.is_file():
            raise ValueError(f"recurso obrigatório ausente/não regular: {name}")
        files.append(path)
    for name in RESOURCE_DIRS:
        directory = source / name
        check_source_path(source, directory)
        if not directory.is_dir():
            raise ValueError(f"diretório de recursos ausente/não regular: {name}")
        for path in sorted(directory.rglob("*")):
            if is_link(path):
                raise ValueError(f"links não são distribuídos: {path.relative_to(source)}")
            if path.is_file() and path.suffix in RESOURCE_SUFFIXES:
                if "__pycache__" not in path.parts:
                    files.append(path)
    return sorted(files, key=lambda path: path.relative_to(source).as_posix())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(source: Path, root: Path, dry_run: bool = False) -> dict:
    source = source.resolve(strict=True)
    root = root.expanduser().absolute()
    destination = root / NAME
    files = manifest(source)
    # Resolve existing ancestors too: installation inside the source would recurse.
    resolved_destination = destination.resolve()
    if resolved_destination == source or source in resolved_destination.parents:
        raise ValueError("a instalação deve ficar fora da árvore do pacote-fonte")
    if is_link(destination):
        raise ValueError("destino é link/junction; escolha uma pasta explícita independente")
    relative = [path.relative_to(source) for path in files]
    state = "would_install" if dry_run else "installed"
    if destination.exists():
        if not destination.is_dir():
            raise ValueError("destino já existe e não é um diretório")
        existing = []
        for path in destination.rglob("*"):
            if is_link(path):
                raise ValueError("instalação existente contém link/junction; nada foi alterado")
            if path.is_file() and "__pycache__" not in path.parts:
                existing.append(path.relative_to(destination))
        if set(existing) != set(relative):
            raise ValueError("destino contém uma instalação diferente; nada foi sobrescrito")
        if any(digest(src) != digest(destination / rel) for src, rel in zip(files, relative)):
            raise ValueError("instalação existente foi alterada; nada foi sobrescrito")
        state = "unchanged"
    elif not dry_run:
        root.mkdir(parents=True, exist_ok=True)
        # Exclusive creation: never use copytree(..., dirs_exist_ok=True).
        destination.mkdir(exist_ok=False)
        try:
            for src, rel in zip(files, relative):
                target = destination / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream:
                    stream.write(src.read_bytes())
        except OSError as exc:
            raise OSError(
                f"instalação interrompida em {destination}; arquivos parciais preservados; "
                f"inspecione o destino antes de tentar novamente: {exc}"
            ) from exc
    return {
        "ok": True,
        "state": state,
        "destination": str(destination),
        "file_count": len(relative),
        "files": [rel.as_posix() for rel in relative],
        "configuration_changed": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="raiz de skills aceita pelo cliente")
    parser.add_argument("--dry-run", action="store_true", help="mostrar destino/manifesto sem gravar")
    args = parser.parse_args(argv)
    try:
        result = install(Path(__file__).resolve().parent.parent, args.root, args.dry_run)
    except (OSError, ValueError, RuntimeError) as exc:
        result = {
            "ok": False,
            "error": str(exc),
            "solution": "corrija o caminho ou escolha uma raiz sem instalação divergente; não há modo force",
        }
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
