"""Shared helpers for the Elory session-isolation build overlays."""
from pathlib import Path
import os

ROOT = Path(os.environ["PROJECT_DIR"]).resolve()
JAVA = "app/src/main/java/com/pinky/dashboard/"
TEST_DEST = ROOT / "app/src/test/java/com/pinky/dashboard/SessionCacheIsolationTest.kt"


def read(path):
    file = ROOT / path
    if not file.is_file():
        raise SystemExit(f"Required Elory source file is missing: {path}")
    return file.read_text(encoding="utf-8")


def write(path, content):
    file = ROOT / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")


def replace(source, old, new, label):
    count = source.count(old)
    if count == 0 and new in source:
        return source
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)


def add_import(source, line, anchor):
    if line in source:
        return source
    if anchor not in source:
        raise SystemExit(f"Missing import anchor for {line}")
    return source.replace(anchor, anchor + line + "\n", 1)
