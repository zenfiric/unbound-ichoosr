from .azure_deepseek import _get_azure
from .openai import _get_openai
from .vm_deepseek import _get_vm_deepseek
from .zai import _get_zai

MODELS = {
    "openai_gpt4o": (_get_openai, "gpt-4o"),
    "openai_gpt5": (_get_openai, "gpt-5"),
    "openai_gpt5mini": (_get_openai, "gpt-5-mini"),
    "azure": (_get_azure, None),
    "vm_deepseek": (_get_vm_deepseek, None),
    "zai_glm45air": (_get_zai, "glm-4.5-air"),
    "zai_glm4.6": (_get_zai, "glm-4.6"),
}


async def get_model_client(model: str, api_key: str | None = None):
    if model not in MODELS:
        raise ValueError(f"Unsupported model: {model}")

    func, model_name = MODELS[model]
    if model_name:
        model_client = await func(api_key, model=model_name)
    else:
        model_client = await func(api_key)
    return model_client


__all__ = ["get_model_client"]
