from typing import TypedDict

from autogen_core.models import ModelInfo


class EndpointsClientArguments(TypedDict, total=False):
    endpoint: str
    api_key: str
    model_info: ModelInfo
    model: str


class EndpointsCreateArguments(TypedDict, total=False):
    frequency_penalty: float | None
    presence_penalty: float | None
    temperature: float | None
    top_p: float | None
    max_tokens: int | None
    stop: list[str] | None
    seed: int | None


class EndpointsChatCompletionClientConfig(
    EndpointsClientArguments, EndpointsCreateArguments
):
    pass
