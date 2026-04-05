from __future__ import annotations

import json
import logging
from typing import Any

import openai

from call_agent.domain.enums import MessageRole
from call_agent.domain.models import Message, Route
from call_agent.repositories import ConversationRepositoryProtocol, SchedulingAPIProtocol
from call_agent.services.prompts import build_system_prompt
from call_agent.services.tools import TOOL_DEFINITIONS, TOOL_REGISTRY

logger = logging.getLogger(__name__)

_MAX_TOOL_ITERATIONS = 10


class AgentService:
    def __init__(
        self,
        openai_client: openai.AsyncOpenAI,
        scheduling_api: SchedulingAPIProtocol,
        conversation_repo: ConversationRepositoryProtocol,
        model: str = "gpt-4o-mini",
    ) -> None:
        self._openai = openai_client
        self._api = scheduling_api
        self._conversation_repo = conversation_repo
        self._model = model

    async def handle_message(
        self, patient_phone: str, route: Route, text: str
    ) -> str:
        messages = await self._conversation_repo.get_messages(
            patient_phone, route.phone_number
        )

        # First message — build and prepend system prompt
        if not messages:
            system_prompt = await self._build_system_prompt(route)
            messages.append(
                Message(role=MessageRole.SYSTEM, content=system_prompt)
            )

        # Append user message
        messages.append(Message(role=MessageRole.USER, content=text))

        # Tool-calling loop
        for _ in range(_MAX_TOOL_ITERATIONS):
            response = await self._call_openai(messages)
            choice = response.choices[0].message

            # Build assistant message
            assistant_msg = Message(
                role=MessageRole.ASSISTANT,
                content=choice.content,
                tool_calls=(
                    [tc.model_dump() for tc in choice.tool_calls]
                    if choice.tool_calls
                    else None
                ),
            )
            messages.append(assistant_msg)

            # If no tool calls, we have the final text response
            if not choice.tool_calls:
                break

            # Execute each tool call
            for tool_call in choice.tool_calls:
                result = await self._execute_tool(tool_call, route)
                messages.append(
                    Message(
                        role=MessageRole.TOOL,
                        content=result,
                        tool_call_id=tool_call.id,
                        name=tool_call.function.name,
                    )
                )

        # Save conversation
        await self._conversation_repo.save_messages(
            patient_phone, route.phone_number, messages
        )

        # Return the last assistant text response
        return self._extract_reply(messages)

    async def _build_system_prompt(self, route: Route) -> str:
        clinic = await self._api.get_clinic(route.clinic_id)
        doctor = None
        if route.doctor_id:
            doctor = await self._api.get_doctor(route.doctor_id)
        return build_system_prompt(route, clinic, doctor)

    async def _call_openai(self, messages: list[Message]) -> Any:
        openai_messages = self._to_openai_messages(messages)
        return await self._openai.chat.completions.create(
            model=self._model,
            messages=openai_messages,  # type: ignore[arg-type]
            tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
        )

    @staticmethod
    def _to_openai_messages(
        messages: list[Message],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for msg in messages:
            entry: dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                entry["content"] = msg.content
            if msg.tool_calls is not None:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_call_id is not None:
                entry["tool_call_id"] = msg.tool_call_id
            if msg.name is not None:
                entry["name"] = msg.name
            result.append(entry)
        return result

    async def _execute_tool(self, tool_call: Any, route: Route) -> str:
        fn_name = tool_call.function.name
        executor = TOOL_REGISTRY.get(fn_name)
        if executor is None:
            return json.dumps({"error": f"Unknown tool: {fn_name}"})

        try:
            args = json.loads(tool_call.function.arguments)
            result: str = await executor(self._api, args, route)
            return result
        except Exception as e:
            logger.exception("Tool %s failed", fn_name)
            return json.dumps({"error": str(e)})

    @staticmethod
    def _extract_reply(messages: list[Message]) -> str:
        for msg in reversed(messages):
            if msg.role == MessageRole.ASSISTANT and msg.content:
                return msg.content
        return "מצטער, לא הצלחתי לעבד את הבקשה. אנא נסה שוב."
