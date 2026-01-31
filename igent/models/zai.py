import os

from autogen_core.models import ModelInfo

from igent.connectors.endpoints import EndpointsChatCompletionClient


async def _get_zai(
    api_key: str | None = None,
    model: str = "glm-4.5-air",
    enable_thinking: bool = False,
) -> EndpointsChatCompletionClient:
    """Create ZhipuAI (Z.AI) chat completion client.

    Args:
        api_key: API key for ZhipuAI (or uses ZAI_API_KEY env var)
        model: Model name (glm-4.5-air, glm-4.6, etc.)
        enable_thinking: Enable chain-of-thought reasoning (slower but more thorough)
                        Default: False for faster responses

    Returns:
        Configured chat completion client

    Note:
        enable_thinking=True adds <thinking> tags and step-by-step reasoning.
        Use False for faster, direct responses (recommended for most tasks).
    """
    API_KEY = api_key or os.getenv("ZAI_API_KEY")

    # Build extra_create_args based on thinking mode
    extra_args = {}
    if not enable_thinking:
        # Disable thinking mode for faster responses
        # For vLLM/SGLang deployments
        extra_args["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}

    model_client = EndpointsChatCompletionClient(
        endpoint="https://api.z.ai/api/paas/v4/",
        api_key=API_KEY,
        model=model,
        model_info=ModelInfo(
            vision=False,
            function_calling=True,
            json_output=True,
            family="gpt-4o",
            structured_output=True,
        ),
        create_args=extra_args,
    )
    return model_client
