#!/usr/bin/env python3
"""Offline package checks for this skill, not a general YAML/spec validator."""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
NAME = "multi-agent-planning-agent-skill"


def check(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    required = (
        "SKILL.md", "README.md", "LICENSE", "references/planning.md",
        "references/execution.md", "references/plan-format.md",
        "references/review-checklist.md", "references/provenance.md",
        "scripts/waveplan.py", "scripts/install.py", "assets/plan.schema.json",
        "examples/plan.json",
    )
    for name in required:
        if not (root / name).is_file():
            errors.append(f"recurso obrigatório ausente: {name}")
    if errors:
        return errors
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    lines = skill.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        errors.append("SKILL.md precisa de frontmatter YAML delimitado")
    else:
        end = lines.index("---", 1)
        fields = {}
        for line in lines[1:end]:
            key, separator, value = line.partition(":")
            if not separator or key in fields:
                errors.append("frontmatter deve usar chaves únicas e valores escalares em uma linha")
                continue
            fields[key] = value.strip()
        if fields.get("name") != NAME or root.name != NAME:
            errors.append("name/folder não correspondem ao nome portátil da skill")
        if not 1 <= len(fields.get("description", "")) <= 1024:
            errors.append("description deve conter de 1 a 1024 caracteres")
        if len(fields.get("compatibility", "")) > 500:
            errors.append("compatibility ultrapassa 500 caracteres")
        if set(fields) - {"name", "description", "license", "compatibility"}:
            errors.append("frontmatter possui campo não previsto pelo contrato local")
        if len(lines[end + 1:]) >= 500:
            errors.append("corpo da skill excede orçamento local de 499 linhas")
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix not in {".md", ".py", ".json", ".yml", ".yaml"}:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.endswith(".local.md") or relative.startswith("publication.local/"):
            continue
        text = path.read_text(encoding="utf-8")
        if text.startswith("\ufeff"):
            errors.append(f"UTF-8 BOM não permitido: {relative}")
        for index, line in enumerate(text.splitlines(), 1):
            if line.rstrip() != line:
                errors.append(f"espaço no fim da linha: {relative}:{index}")
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError as exc:
                errors.append(f"JSON inválido: {relative}: {exc}")
        if path.suffix == ".py":
            try:
                ast.parse(text, filename=relative)
            except SyntaxError as exc:
                errors.append(f"Python inválido: {relative}: {exc}")
        if path.suffix == ".md":
            for match in re.finditer(r'\[[^\]\n]*\]\((?:<([^>]+)>|([^\)]+))\)', text):
                target = match.group(1) or match.group(2)
                if urlsplit(target).scheme or target.startswith("#"):
                    continue
                local = unquote(target.split("#", 1)[0])
                if local and not (path.parent / local).exists():
                    errors.append(f"link interno inexistente: {relative} -> {local}")
        if relative.startswith(".github/workflows/"):
            if not re.search(r'^permissions:', text, re.M):
                errors.append(f"workflow sem permissions: {relative}")
            for match in re.finditer(r'uses:\s*([^\s#]+)', text):
                if not re.fullmatch(r'[\w.-]+/[\w./-]+@[a-f0-9]{40}', match.group(1)):
                    errors.append(f"action sem SHA: {relative}: {match.group(1)}")
            if "<PIN_SHA>" in text:
                errors.append(f"workflow ainda contém pin indefinido: {relative}")
    contracts = [root / "AGENTS.md", root / "CLAUDE.md"]
    if all(path.exists() for path in contracts):
        if contracts[0].read_bytes() != contracts[1].read_bytes():
            errors.append("AGENTS.md e CLAUDE.md divergiram")
    helper = ast.parse((root / "scripts/waveplan.py").read_text(encoding="utf-8"))
    forbidden = {"subprocess", "socket", "http", "requests", "openai", "urllib"}
    for node in ast.walk(helper):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [(node.module or "").split(".")[0]]
        else:
            continue
        if forbidden.intersection(modules):
            errors.append("helper importa módulo de execução/rede proibido pelo escopo")
    return errors


def main() -> int:
    errors = check()
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        print(f"Erro: {len(errors)} falhas no pacote — Solução: corrigir e repetir check_skill.py")
        return 1
    print("PASS: pacote, frontmatter local, links, JSON, Python, formato e pins")
    print("Nota: verificação offline local; não substitui skills-ref nem revisão semântica.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
