from typing import IO
from share import format as fmt

def setattrdefault[T]( namespace, field:str, default:T ) -> T:
    """Safely set a default attribute on a namespace if it doesn't exist.

    Args:
        namespace: The target namespace.
        field: The attribute name to set/check.
        default: Value to assign if missing.

    Returns:
        The existing value if present, otherwise the default (after setting it).
    """
    existing = getattr( namespace, field, None ) # type: ignore[attr-defined]
    if existing: return existing
    setattr(namespace, field, default) # type: ignore[attr-defined]
    return default


def get_interior_dict( subject ) -> dict:
    """Return a plain dict of all attributes from an object (usually a SimpleNamespace)."""
    return {k: v for k, v in subject.__dict__.items()}


def process_log_null( raw_file: IO, clean_file: IO ):
    """Strip ANSI escape sequences from raw log lines and write cleaned output.

    Args:
        raw_file: Readable text stream containing raw (coloured) logs.
        clean_file: Writable text stream for cleaned output.
    """
    regex = fmt.re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')

    for line in raw_file:
        clean_file.write( regex.sub('', line ) )
