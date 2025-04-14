from pathlib import Path


def construct_file_path(
    filepath: str | Path, constellation: str, business_line: str, model: str
) -> Path:
    """Construct a file path with configuration, business_line, and model prefix."""
    path = Path(filepath)
    return path.parent / f"{constellation}_{business_line}_{model}_{path.name}"
