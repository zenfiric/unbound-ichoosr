from .azure_deepseek import _get_azure
from .openai import _get_openai

MODELS = {"openai": _get_openai, "azure": _get_azure}


async def get_model_client(model: str, api_key: str | None = None):
    if model not in MODELS:
        raise ValueError(f"Unsupported model: {model}")

    model_client = await MODELS[model](api_key)
    return model_client


__all__ = ["get_model_client"]
