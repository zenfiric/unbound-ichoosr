from pathlib import Path


def construct_file_path(
    filepath: str | Path, configuration: str, business_line: str, model: str
) -> Path:
    """Construct a file path with configuration, business_line, and model prefix."""
    path = Path(filepath)
    return path.parent / f"{configuration}_{business_line}_{model}_{path.name}"
