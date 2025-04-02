import os

from autogen_core.models import ModelInfo
from autogen_ext.models.azure import AzureAIChatCompletionClient
from azure.core.credentials import AzureKeyCredential

ENDPOINT_URL = "https://aiservices-pom-poc-westeu-001.services.ai.azure.com/models/"
API_VERSION = "2024-05-01-preview"


async def _get_azure(api_key: str | None = None, model: str = "DeepSeek-V3"):
    API_KEY = api_key or os.getenv("AZUREAI_API_KEY")
    model_client = AzureAIChatCompletionClient(
        model=model,
        endpoint=ENDPOINT_URL,
        credential=AzureKeyCredential(API_KEY),
        api_version=API_VERSION,
        model_info=ModelInfo(
            name="DeepSeek-V3",
            vision=False,
            function_calling=True,
            json_output=False,
            family="r1",
        ),
    )
    return model_client
