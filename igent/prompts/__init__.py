from pathlib import Path

from igent.tools.read_txt import read_txt

# Define the base path for prompts
PROMPTS_DIR = Path(__file__).parent


async def load_prompts(biz_line: str, variant: str | None = None) -> dict[str, str]:
    """
    Asynchronously load prompt files from the prompts directory based on business line and variant.

    Args:
        biz_line (str): The business line (e.g., 'enuk', 'sbus').
        variant (str | None): Optional subdirectory variant (e.g., 'no_critic', 'one_critic').
            If None, loads top-level prompts.

    Returns:
        dict: A dictionary mapping prompt names to their contents.

    Raises:
        FileNotFoundError: If a required prompt file is missing.
    """
    prompts = {}
    base_path = PROMPTS_DIR / biz_line

    if variant:
        base_path = base_path / variant

    try:
        if variant == "no_critic" and biz_line == "sbus":
            prompts["a_matcher"] = await read_txt(
                str(base_path / "sbus_a_matcher_no_crit.txt")
            )
            prompts["b_matcher"] = await read_txt(
                str(base_path / "sbus_b_matcher_no_crit.txt")
            )
            # No critics in this variant
        elif variant == "one_critic" and biz_line == "sbus":
            prompts["a_matcher"] = await read_txt(str(base_path / "sbus_a_matcher.txt"))
            prompts["b_matcher"] = await read_txt(str(base_path / "sbus_b_matcher.txt"))
            prompts["critic"] = await read_txt(
                str(base_path / "sbus_a_and_b_critic.txt")
            )
        else:
            # Default case: load top-level prompts for biz_line (enuk or sbus)
            prompts["a_matcher"] = await read_txt(
                str(base_path / f"{biz_line}_a_matcher.txt")
            )
            prompts["a_critic"] = await read_txt(
                str(base_path / f"{biz_line}_a_critic.txt")
            )
            prompts["b_matcher"] = await read_txt(
                str(base_path / f"{biz_line}_b_matcher.txt")
            )
            prompts["b_critic"] = await read_txt(
                str(base_path / f"{biz_line}_b_critic.txt")
            )
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Missing prompt file for {biz_line}/{variant}: {e}")

    return prompts


__all__ = ["load_prompts"]
