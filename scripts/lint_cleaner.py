#!/usr/bin/env python3
"""
Khulaasaa Architecture & Code Cleanliness Linter.
Checks:
1. Max script lines (< 500 lines for every .py and .js file).
2. Zero emoji policy in code, web templates, and Telegram alert formatters.
3. Python syntax integrity across all modules.
"""
from __future__ import annotations

import os
import py_compile
import sys
from pathlib import Path

MAX_LINES = 500
IGNORE_DIRS = {".git", ".venv", "__pycache__", "scratch", "node_modules", ".gemini"}


def check_line_counts(root_dir: Path) -> list[str]:
    violations = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith(".py") or f.endswith(".js"):
                path = Path(root) / f
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                        lines = len(fp.readlines())
                    if lines > MAX_LINES:
                        violations.append(f"{lines:4d} lines (exceeds {MAX_LINES}): {path.as_posix()}")
                except Exception as e:
                    violations.append(f"Error reading {path}: {e}")
    return violations


def check_zero_emojis(root_dir: Path) -> list[str]:
    violations = []
    # Strict zero-emoji policy applies to Telegram bot code and web templates
    check_paths = [
        root_dir / "alerts" / "telegram.py",
        root_dir / "alerts" / "telegram_formatters.py",
        root_dir / "alerts" / "telegram_bot.py",
        root_dir / "alerts" / "telegram_client.py",
        root_dir / "alerts" / "telegram_keyboards.py",
        root_dir / "templates",
    ]
    for target in check_paths:
        if not target.exists():
            continue
        files_to_check = [target] if target.is_file() else list(target.rglob("*.html"))
        for p in files_to_check:
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                found = [
                    c for c in text
                    if (0x1F300 <= ord(c) <= 0x1F9FF)
                    or (0x1FA70 <= ord(c) <= 0x1FAFF)
                ]
                if found:
                    hex_codes = [f"U+{ord(c):04X}" for c in found[:5]]
                    violations.append(f"Found {len(found)} emoji(s) {hex_codes} in {p.relative_to(root_dir).as_posix()}")
            except Exception as e:
                violations.append(f"Error checking {p}: {e}")
    return violations


def check_python_syntax(root_dir: Path) -> list[str]:
    violations = []
    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f.endswith(".py"):
                path = Path(root) / f
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as err:
                    violations.append(f"Syntax error in {path.as_posix()}: {err}")
    return violations


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    print(f"Running Khulaasaa Code Cleanliness Checker on {root}...")

    line_violations = check_line_counts(root)
    emoji_violations = check_zero_emojis(root)
    syntax_violations = check_python_syntax(root)

    total_violations = len(line_violations) + len(emoji_violations) + len(syntax_violations)

    print("\n--- 1. Max Lines Check (< 500 lines) ---")
    if line_violations:
        for v in line_violations:
            print(f"  FAIL: {v}")
    else:
        print("  PASS: All Python and JS files are strictly under 500 lines.")

    print("\n--- 2. Zero-Emoji Design Policy Check ---")
    if emoji_violations:
        for v in emoji_violations:
            print(f"  FAIL: {v}")
    else:
        print("  PASS: Zero emojis found across Telegram alerts and Web Templates.")

    print("\n--- 3. Python Syntax Verification ---")
    if syntax_violations:
        for v in syntax_violations:
            print(f"  FAIL: {v}")
    else:
        print("  PASS: All Python modules compile cleanly.")

    print(f"\nResult: {'SUCCESS' if total_violations == 0 else 'FAILURE'} ({total_violations} issues)")
    return 0 if total_violations == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
