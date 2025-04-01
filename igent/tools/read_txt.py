import aiofiles
from autogen_core.tools import FunctionTool


async def read_txt(file_path: str) -> str:
    """Reads the contents of a text file asynchronously.

    Args:
        file_path (str): Path to the text file to read.

    Returns:
        str: Contents of the file as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        IOError: If there's an error reading the file.
    """
    try:
        async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
            content = await file.read()
        return content
    except FileNotFoundError as fnf_err:
        raise FileNotFoundError(f"File not found: {file_path}") from fnf_err
    except IOError as io_err:
        raise IOError(f"Error reading file {file_path}") from io_err


read_txt_tool = FunctionTool(
    read_txt,
    description="Reads the contents of a text file asynchronously and returns it as a string.",
)
