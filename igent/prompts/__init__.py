from pathlib import Path

from igent.tools import read_txt

# Define the base path for prompts
PROMPTS_DIR = Path(__file__).parent


async def load_prompts(biz_line: str) -> dict[str, str]:
    """
    Asynchronously load prompt files from the prompts directory.

    Returns:
        dict: A dictionary mapping prompt names to their contents.
    """
    return {
        "a_matcher": await read_txt(
            str(PROMPTS_DIR / biz_line / f"{biz_line}_a_matcher.txt")
        ),
        "a_critic": await read_txt(
            str(PROMPTS_DIR / biz_line / f"{biz_line}_a_critic.txt")
        ),
        "b_matcher": await read_txt(
            str(PROMPTS_DIR / biz_line / f"{biz_line}_b_matcher.txt")
        ),
        "b_critic": await read_txt(
            str(PROMPTS_DIR / biz_line / f"{biz_line}_b_critic.txt")
        ),
    }


# Make load_prompts available when importing the module
__all__ = ["load_prompts"]
