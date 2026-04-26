"""
LangChain tool-calling agent — Groq Llama 3.3 70B.
The LLM decides which tools to call. If tools return no data,
the LLM still answers from its own agricultural knowledge.
"""
import os
import time
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from groq import RateLimitError
from .tools.weather import weather_tool
from .tools.market import market_tool
from .tools.rag import rag_tool
from .tools.pest import pest_advice_tool

TOOLS = [weather_tool, market_tool, rag_tool, pest_advice_tool]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

SYSTEM_PROMPT = """You are Kisan AI (ਕਿਸਾਨ ਏਆਈ), an expert AI assistant for small farmers in Punjab, India.
You have deep knowledge of Punjab agriculture: crops, fertilizers, irrigation, pest management, mandi prices, government schemes, and weather.

TOOLS AVAILABLE:
- weather_tool: live weather for any Punjab city
- market_tool: live mandi prices from Agmarknet
- rag_tool: Punjab agriculture knowledge base
- pest_advice_tool: crop disease treatment advice

RULES:
- For price questions: call market_tool first. If no data, use your own knowledge of typical Punjab mandi prices.
- For weather questions: call weather_tool.
- For crop/fertilizer/scheme questions: call rag_tool, then answer.
- For disease/pest questions: call pest_advice_tool.
- NEVER say "I don't know" — always give a useful answer from your expertise.
- If a tool fails, answer from your own agricultural knowledge.
- Respond in {language}. Keep answers concise, practical, farmer-friendly.
- Farmer location: {location}
"""


def _make_llm(bind_tools=True):
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=800,
    )
    return llm.bind_tools(TOOLS) if bind_tools else llm


def _invoke_with_retry(llm, messages, retries=3):
    """Invoke LLM with exponential backoff on rate limit errors."""
    for attempt in range(retries):
        try:
            return llm.invoke(messages)
        except RateLimitError:
            if attempt == retries - 1:
                raise
            time.sleep(8 * (attempt + 1))  # 8s, 16s, 24s
    raise RuntimeError("LLM unavailable after retries")


def run_agent(query: str, language: str = "en", location: str = "Punjab") -> str:
    """Blocking call — returns full response string. Used as AJAX fallback."""
    llm = _make_llm(bind_tools=True)
    lang_display = {"en": "English", "hi": "Hindi", "pa": "Punjabi (Gurmukhi script)"}.get(language, "English")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(language=lang_display, location=location)),
        HumanMessage(content=query),
    ]

    try:
        for _ in range(4):
            response: AIMessage = _invoke_with_retry(llm, messages)
            messages.append(response)

            if not response.tool_calls:
                return response.content or "Sorry, I could not generate a response."

            for tc in response.tool_calls:
                tool_fn = TOOLS_BY_NAME.get(tc["name"])
                try:
                    result = tool_fn.invoke(tc["args"]) if tool_fn else f"Unknown tool: {tc['name']}"
                except Exception as e:
                    result = f"Tool error: {e}. Answer from your own knowledge."
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        # Max iterations — get final answer without tools
        final = _invoke_with_retry(_make_llm(bind_tools=False), messages)
        return final.content or "Sorry, I could not process your request."

    except RateLimitError:
        return "The AI service is temporarily busy. Please wait 10-15 seconds and try again."
    except Exception:
        return "Sorry, an error occurred. Please try again."


def run_agent_stream(query: str, language: str = "en", location: str = "Punjab"):
    """
    Generator — yields text chunks as they arrive from the LLM.
    Tool-calling phase is blocking; final answer streams token by token.
    """
    lang_display = {"en": "English", "hi": "Hindi", "pa": "Punjabi (Gurmukhi script)"}.get(language, "English")
    llm_tools = _make_llm(bind_tools=True)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(language=lang_display, location=location)),
        HumanMessage(content=query),
    ]

    try:
        # Tool-calling phase (non-streaming — tools need complete responses)
        for _ in range(3):
            response = _invoke_with_retry(llm_tools, messages)
            messages.append(response)

            if not response.tool_calls:
                # LLM answered directly without tools — yield word by word
                words = (response.content or "").split(" ")
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                return

            for tc in response.tool_calls:
                tool_fn = TOOLS_BY_NAME.get(tc["name"])
                try:
                    result = tool_fn.invoke(tc["args"]) if tool_fn else f"Unknown tool: {tc['name']}"
                except Exception as e:
                    result = f"Tool error: {e}. Answer from your own knowledge."
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

        # After tool calls — stream the final synthesized answer
        llm_stream = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
            max_tokens=800,
            streaming=True,
        )
        for chunk in llm_stream.stream(messages):
            if chunk.content:
                yield chunk.content

    except RateLimitError:
        yield "The AI service is temporarily busy. Please wait 10-15 seconds and try again."
    except Exception:
        yield "Sorry, an error occurred. Please try again."
