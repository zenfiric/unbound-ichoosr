from autogen_core.models import ModelInfo
from autogen_ext.models.ollama import OllamaChatCompletionClient

VM_HOST = "http://172.205.181.57:11434"


async def _get_vm_deepseek(api_key: str | None = None, model: str = "deepseek-r1:14b"):
    model_client = OllamaChatCompletionClient(
        model=model,
        host=VM_HOST,
        model_info=ModelInfo(
            name="DeepSeek-R1",
            vision=False,
            function_calling=True,
            json_output=False,
            family="r1",
        ),
    )
    return model_client
