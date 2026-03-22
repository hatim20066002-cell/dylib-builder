import os
from pathlib import Path


def detect_language(source_dir: str) -> str | None:
    """
    Detect the primary programming language in the project directory.
    Returns: 'c', 'cpp', 'swift', 'objc', or None if unsupported.
    """
    counts = {"swift": 0, "cpp": 0, "objc": 0, "c": 0}

    for root, _, files in os.walk(source_dir):
        for f in files:
            ext = Path(f).suffix.lower()
            if ext == '.swift':
                counts['swift'] += 1
            elif ext in ('.cpp', '.cxx', '.cc'):
                counts['cpp'] += 1
            elif ext in ('.m', '.mm'):
                counts['objc'] += 1
            elif ext == '.c':
                counts['c'] += 1

    for lang in ['swift', 'cpp', 'objc', 'c']:
        if counts[lang] > 0:
            return lang

    return None


LANG_EMOJI = {
    "c": "🔵",
    "cpp": "🟣",
    "swift": "🟠",
    "objc": "🔴"
}

LANG_NAME = {
    "c": "C",
    "cpp": "C++",
    "swift": "Swift",
    "objc": "Objective-C"
}
