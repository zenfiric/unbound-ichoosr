import os

from autogen_ext.models.openai import OpenAIChatCompletionClient


async def _get_openai(api_key: str | None = None, model: str = "gpt-4o"):
    API_KEY = api_key or os.getenv("OPENAI_API_KEY")
    model_client = OpenAIChatCompletionClient(model=model, api_key=API_KEY)
    return model_client
