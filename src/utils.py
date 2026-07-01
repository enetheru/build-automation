#!/usr/bin/env python
"""Utility functions extracted for reuse across build system."""
from types import SimpleNamespace
from typing import IO, TypeVar

T = TypeVar('T')


def setattrdefault(namespace: SimpleNamespace, field: str, default: T) -> T:
    """Safely set a default attribute on a namespace if it doesn't exist."""
    existing = getattr(namespace, field, None)
    if existing:
        return existing
    setattr(namespace, field, default)
    return default


def get_interior_dict(subject) -> dict:
    """Return a plain dict of all attributes from an object (usually a SimpleNamespace)."""
    return {k: v for k, v in subject.__dict__.items()}


def process_log_null(raw_file: IO, clean_file: IO):
    """Strip ANSI escape sequences from raw log lines and write cleaned output."""
    import re
    regex = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
    for line in raw_file:
        clean_file.write(regex.sub('', line))
