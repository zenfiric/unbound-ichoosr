import os

from autogen_core.models import ModelInfo

from igent.connectors.endpoints import EndpointsChatCompletionClient


async def _get_zai(api_key: str | None = None, model: str = "glm-4.5-air"):
    API_KEY = api_key or os.getenv("ZAI_API_KEY")
    model_client = EndpointsChatCompletionClient(
        endpoint="https://api.z.ai/api/paas/v4/",
        api_key=API_KEY,
        model=model,
        model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=False,
            family="gpt-4o",
            structured_output=False,
        ),
    )
    return model_client
