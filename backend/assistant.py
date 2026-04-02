"""
assistant.py  (performance tuned)
-----------------------------------
Key changes:
- System prompt is much shorter — fewer tokens = faster responses
- Long-term memory search skipped if message is very short (< 10 chars)
- Tool loop capped at 1 round to minimise latency on slow machines
- History trimmed to last MEMORY_WINDOW messages before sending
"""

import os
import asyncio
import re
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from backend.router import get_llm, get_mode, LLM_TIMEOUT
from backend.memory import short_term, long_term
from backend.tools import TOOL_REGISTRY

load_dotenv()

ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Nova")
USER_NAME      = os.getenv("USER_NAME",      "Friend")
MEMORY_WINDOW  = int(os.getenv("MEMORY_WINDOW", "10"))


def build_system_prompt(memories: list[str]) -> str:
    # SHORTER prompt = fewer tokens = faster first token
    tools_text = "\n".join(
        f"- {name}: {info['description']}"
        for name, info in TOOL_REGISTRY.items()
    )
    mem_text = ""
    if memories:
        mem_text = "\nPast context:\n" + "\n".join(f"- {m[:200]}" for m in memories)

    mode_label = "online (internet available)" if get_mode() == "online" else "offline (local model)"

    return (
        f"You are {ASSISTANT_NAME}, a concise and helpful personal AI assistant for {USER_NAME}. "
        f"Mode: {mode_label}.\n"
        "Be brief and direct. Use markdown for code and lists.\n\n"
        "To use a tool respond with:\nTOOL: <name>\nINPUT: <value>\n\n"
        f"Tools:\n{tools_text}"
        f"{mem_text}"
    )


def extract_tool_call(text: str):
    match = re.search(r"TOOL:\s*(\w+)\s*\nINPUT:\s*(.*)", text, re.DOTALL)
    return (match.group(1).strip(), match.group(2).strip()) if match else None


async def _invoke_llm(messages):
    """Run llm.invoke in a thread so it doesn't block the async event loop."""
    llm = get_llm()
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(None, lambda: llm.invoke(messages)),
        timeout=LLM_TIMEOUT,
    )


async def chat(user_message: str) -> str:
    # Only search long-term memory for longer messages (saves time)
    memories = long_term.search(user_message, n=2) if len(user_message) > 10 else []

    system = SystemMessage(content=build_system_prompt(memories))

    # Trim history to last MEMORY_WINDOW pairs to keep prompt small
    history = short_term.get_history()[-(MEMORY_WINDOW * 2):]
    history_msgs = [
        HumanMessage(content=m["content"]) if m["role"] == "user"
        else AIMessage(content=m["content"])
        for m in history
    ]

    messages = [system] + history_msgs + [HumanMessage(content=user_message)]

    try:
        response = await _invoke_llm(messages)
        reply = response.content
    except asyncio.TimeoutError:
        return (
            f"⏱ Model timed out after {LLM_TIMEOUT}s.\n\n"
            "**Quick fixes:**\n"
            "1. Switch to a lighter model — set `OFFLINE_MODEL=phi3:mini` in `.env`\n"
            "2. Lower `OLLAMA_NUM_CTX=512` in `.env` to use less RAM\n"
            "3. Close other apps to free up memory\n"
            "4. Run `ollama serve` in a separate terminal before starting"
        )
    except RuntimeError as e:
        return f"⚠️ {e}"
    except Exception as e:
        return f"⚠️ Error: {type(e).__name__}: {e}"

    # Tool call — max 1 round on slow machines
    tool_call = extract_tool_call(reply)
    if tool_call:
        tool_name, tool_input = tool_call
        if tool_name in TOOL_REGISTRY:
            tool_result = TOOL_REGISTRY[tool_name]["fn"](tool_input)
            messages.append(AIMessage(content=reply))
            messages.append(HumanMessage(
                content=f"TOOL_RESULT: {tool_result}\nGive your final answer now."
            ))
            try:
                response = await _invoke_llm(messages)
                reply = response.content
            except (asyncio.TimeoutError, Exception):
                reply = f"Tool result: {tool_result}"

    short_term.add("user", user_message)
    short_term.add("assistant", reply)
    long_term.save(user_message, reply)

    return reply


def clear_session():
    short_term.clear()
