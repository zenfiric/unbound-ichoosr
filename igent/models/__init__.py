from .azure_deepseek import _get_azure
from .openai import _get_openai
from .vm_deepseek import _get_vm_deepseek
from .zai import _get_zai

MODELS = {
    "openai_gpt4o": _get_openai,
    "azure": _get_azure,
    "vm_deepseek": _get_vm_deepseek,
    "zai_glm45air": _get_zai,
}


async def get_model_client(model: str, api_key: str | None = None):
    if model not in MODELS:
        raise ValueError(f"Unsupported model: {model}")

    model_client = await MODELS[model](api_key)
    return model_client


__all__ = ["get_model_client"]
