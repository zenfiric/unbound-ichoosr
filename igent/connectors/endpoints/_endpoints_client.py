import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List, Mapping, Optional, Sequence, Union

from autogen_core import EVENT_LOGGER_NAME, CancellationToken, FunctionCall, Image
from autogen_core.logging import LLMStreamEndEvent, LLMStreamStartEvent
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    ModelInfo,
    RequestUsage,
    SystemMessage,
    UserMessage,
    validate_model_info,
)
from autogen_core.tools import Tool, ToolSchema
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

logger = logging.getLogger(EVENT_LOGGER_NAME)


def _to_openai_message(message: LLMMessage) -> List[Dict[str, Any]]:
    if isinstance(message, SystemMessage):
        return [{"role": "system", "content": message.content}]
    elif isinstance(message, UserMessage):
        if isinstance(message.content, str):
            return [{"role": "user", "content": message.content}]
        else:
            content = []
            for part in message.content:
                if isinstance(part, str):
                    content.append({"type": "text", "text": part})
                elif isinstance(part, Image):
                    content.append(
                        {"type": "image_url", "image_url": {"url": part.data_uri}}
                    )
                else:
                    raise ValueError(f"Unknown content type: {part}")
            return [{"role": "user", "content": content}]
    elif isinstance(message, AssistantMessage):
        if isinstance(message.content, str):
            return [{"role": "assistant", "content": message.content}]
        else:
            tool_calls = [
                {
                    "id": fc.id,
                    "type": "function",
                    "function": {"name": fc.name, "arguments": fc.arguments},
                }
                for fc in message.content
            ]
            return [{"role": "assistant", "content": None, "tool_calls": tool_calls}]
    else:  # FunctionExecutionResultMessage
        return [
            {"role": "tool", "tool_call_id": x.call_id, "content": x.content}
            for x in message.content
        ]


def convert_tools(tools: Sequence[Tool | ToolSchema]) -> List[Dict[str, Any]]:
    result = []
    for tool in tools:
        if isinstance(tool, Tool):
            tool_schema = tool.schema.copy()
        else:
            tool_schema = tool.copy()
        if "parameters" in tool_schema:
            for value in tool_schema["parameters"]["properties"].values():
                if "title" in value:
                    del value["title"]
        function_def = {
            "name": tool_schema["name"],
            "parameters": tool_schema.get("parameters", {}),
        }
        if "description" in tool_schema:
            function_def["description"] = tool_schema["description"]
        result.append({"type": "function", "function": function_def})
    return result


class EndpointsChatCompletionClient(ChatCompletionClient):
    """
    Chat completion client for models hosted on OpenAI-compatible endpoints (e.g., Hugging Face Endpoints).

    Args:
        endpoint (str): The endpoint URL (e.g., "https://api-inference.huggingface.co/models/..."). **Required.**
        api_key (str): The API key for authentication. **Required.**
        model (str): The name of the model (e.g., "deepseek-r1:1.5b"). **Required.**
        model_info (ModelInfo): The capabilities of the model (e.g., vision, json_output). **Required.**
        frequency_penalty (float, optional): Frequency penalty for generation.
        presence_penalty (float, optional): Presence penalty for generation.
        temperature (float, optional): Sampling temperature.
        top_p (float, optional): Top-p sampling probability.
        max_tokens (int, optional): Maximum tokens to generate.
        stop (List[str], optional): Stop sequences.
        seed (int, optional): Random seed for reproducibility.

    Example usage:

    ```python
    import asyncio
    from autogen_core.models import UserMessage
    from endpoints_client import EndpointsChatCompletionClient  # Adjust import path

    async def main():
        client = EndpointsChatCompletionClient(
            endpoint="https://your-huggingface-endpoint",
            api_key="your-api-key",
            model="deepseek-r1:1.5b",
            model_info={
                "json_output": True,
                "function_calling": True,
                "vision": False,
                "family": "unknown",
                "structured_output": False,
            },
        )
        result = await client.create([UserMessage(content="Hello, world!", source="user")])
        print(result.content)
        await client.close()

    if __name__ == "__main__":
        asyncio.run(main())
    ```

    Requires the `openai` package:

    ```bash
    pip install openai
    ```
    """

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        model: str,
        model_info: ModelInfo,
        **kwargs: Any,
    ):
        config = self._validate_config(
            {
                "endpoint": endpoint,
                "api_key": api_key,
                "model": model,
                "model_info": model_info,
                **kwargs,
            }
        )
        self._model_info = config["model_info"]
        self._client = self._create_client(config)
        self._create_args = self._prepare_create_args(config)
        self._actual_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self._total_usage = RequestUsage(prompt_tokens=0, completion_tokens=0)

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        for key in ["endpoint", "api_key", "model", "model_info"]:
            if key not in config:
                raise ValueError(f"{key} is required for EndpointsChatCompletionClient")
        validate_model_info(config["model_info"])
        return config

    @staticmethod
    def _create_client(config: Dict[str, Any]) -> AsyncOpenAI:
        return AsyncOpenAI(base_url=config["endpoint"], api_key=config["api_key"])

    @staticmethod
    def _prepare_create_args(config: Mapping[str, Any]) -> Dict[str, Any]:
        valid_args = {
            "model",
            "frequency_penalty",
            "presence_penalty",
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "seed",
        }
        return {k: v for k, v in config.items() if k in valid_args and v is not None}

    def add_usage(self, usage: RequestUsage) -> None:
        self._total_usage = RequestUsage(
            self._total_usage.prompt_tokens + usage.prompt_tokens,
            self._total_usage.completion_tokens + usage.completion_tokens,
        )

    def _validate_model_info(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[Tool | ToolSchema],
        json_output: Optional[bool | type],
        create_args: Dict[str, Any],
    ) -> None:
        if not self.model_info["vision"]:
            for message in messages:
                if isinstance(message, UserMessage) and isinstance(
                    message.content, list
                ):
                    if any(isinstance(x, Image) for x in message.content):
                        raise ValueError(
                            "Model does not support vision and image was provided"
                        )
        if json_output is not None:
            if not self.model_info["json_output"] and json_output is True:
                raise ValueError("Model does not support JSON output")
            if isinstance(json_output, type):
                raise ValueError("Structured output is not supported")
            if json_output and "response_format" not in create_args:
                create_args["response_format"] = {"type": "json_object"}
        if not self.model_info["function_calling"] and tools:
            raise ValueError("Model does not support function calling")

    async def create(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> CreateResult:
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)
        self._validate_model_info(messages, tools, json_output, create_args)

        openai_messages = [msg for m in messages for msg in _to_openai_message(m)]

        if tools:
            create_args["tools"] = convert_tools(tools)

        task = asyncio.create_task(
            self._client.chat.completions.create(
                messages=openai_messages, **create_args
            )
        )
        if cancellation_token:
            cancellation_token.link_future(task)

        result: ChatCompletion = await task
        choice = result.choices[0]

        if choice.finish_reason == "tool_calls":
            content = [
                FunctionCall(
                    id=tc.id, name=tc.function.name, arguments=tc.function.arguments
                )
                for tc in choice.message.tool_calls
            ]
            finish_reason = "function_calls"
        else:
            content = choice.message.content or ""
            finish_reason = choice.finish_reason

        usage = RequestUsage(
            prompt_tokens=result.usage.prompt_tokens if result.usage else 0,
            completion_tokens=result.usage.completion_tokens if result.usage else 0,
        )

        response = CreateResult(
            finish_reason=finish_reason,
            content=content,
            usage=usage,
            cached=False,
        )
        self.add_usage(usage)
        return response

    async def create_stream(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[Tool | ToolSchema] = [],
        json_output: Optional[bool | type] = None,
        extra_create_args: Mapping[str, Any] = {},
        cancellation_token: Optional[CancellationToken] = None,
    ) -> AsyncGenerator[Union[str, CreateResult], None]:
        create_args = self._create_args.copy()
        create_args.update(extra_create_args)
        self._validate_model_info(messages, tools, json_output, create_args)

        openai_messages = [msg for m in messages for msg in _to_openai_message(m)]
        if tools:
            create_args["tools"] = convert_tools(tools)
        create_args["stream"] = True

        task = asyncio.create_task(
            self._client.chat.completions.create(
                messages=openai_messages, **create_args
            )
        )
        if cancellation_token:
            cancellation_token.link_future(task)

        content_deltas = []
        full_tool_calls = {}
        finish_reason = None
        first_chunk = True

        async for chunk in await task:
            if first_chunk:
                first_chunk = False
                logger.info(LLMStreamStartEvent(messages=[m for m in openai_messages]))
            choice = chunk.choices[0] if chunk.choices else None
            if choice:
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                    if finish_reason == "tool_calls":
                        finish_reason = "function_calls"
                if choice.delta.content:
                    content_deltas.append(choice.delta.content)
                    yield choice.delta.content
                if choice.delta.tool_calls:
                    for tc in choice.delta.tool_calls:
                        idx = tc.index if tc.index is not None else tc.id
                        if idx not in full_tool_calls:
                            full_tool_calls[idx] = {
                                "id": "",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            full_tool_calls[idx]["id"] += tc.id
                        if tc.function.name:
                            full_tool_calls[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            full_tool_calls[idx]["function"][
                                "arguments"
                            ] += tc.function.arguments

        if finish_reason is None:
            raise ValueError("No stop reason found")

        content = (
            [
                FunctionCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=tc["function"]["arguments"],
                )
                for tc in full_tool_calls.values()
            ]
            if finish_reason == "function_calls"
            else "".join(content_deltas)
        )
        usage = RequestUsage(
            prompt_tokens=0, completion_tokens=0
        )  # Usage not available in streaming

        result = CreateResult(
            finish_reason=finish_reason, content=content, usage=usage, cached=False
        )
        logger.info(
            LLMStreamEndEvent(
                response=result.model_dump(), prompt_tokens=0, completion_tokens=0
            )
        )
        yield result

    async def close(self) -> None:
        await self._client.close()

    def actual_usage(self) -> RequestUsage:
        return self._actual_usage

    def total_usage(self) -> RequestUsage:
        return self._total_usage

    def count_tokens(
        self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []
    ) -> int:
        return 0

    def remaining_tokens(
        self, messages: Sequence[LLMMessage], *, tools: Sequence[Tool | ToolSchema] = []
    ) -> int:
        return 0

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info
