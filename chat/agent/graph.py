"""
LangChain tool-calling agent — Groq Llama 3.1 70B.
The LLM decides which tools to call. If tools return no data,
the LLM still answers from its own agricultural knowledge.
"""
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
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
- For price questions: ALWAYS call market_tool first. If it returns no data, answer using your own knowledge of typical Punjab mandi prices.
- For weather questions: ALWAYS call weather_tool.
- For crop/fertilizer/scheme questions: call rag_tool to get knowledge base context, then answer.
- For disease/pest questions: call pest_advice_tool.
- NEVER say "I don't know" or "I can't answer" — you are an expert, always give a useful answer.
- If a tool fails or returns no data, use your own agricultural expertise to answer.
- You can answer general farming questions directly without tools if no real-time data is needed.
- Always respond in {language}.
- Keep answers practical, specific, and farmer-friendly. No jargon.
- For prices, always give context: is it a good time to sell? Compare to MSP if relevant.
- Farmer's location: {location}
"""


def _make_llm():
    """Create a fresh LLM instance — not cached so language/location always applies."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=1500,
    ).bind_tools(TOOLS)


def run_agent(query: str, language: str = "en", location: str = "Punjab") -> str:
    llm = _make_llm()

    lang_display = {"en": "English", "hi": "Hindi", "pa": "Punjabi (Gurmukhi script)"}.get(language, "English")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.format(language=lang_display, location=location)),
        HumanMessage(content=query),
    ]

    for _ in range(5):
        response: AIMessage = llm.invoke(messages)
        messages.append(response)

        # No tool calls — LLM gave a direct answer
        if not response.tool_calls:
            return response.content or "Sorry, I could not generate a response."

        # Run each tool
        for tc in response.tool_calls:
            tool_fn = TOOLS_BY_NAME.get(tc["name"])
            try:
                result = tool_fn.invoke(tc["args"]) if tool_fn else f"Unknown tool: {tc['name']}"
            except Exception as e:
                result = f"Tool error ({tc['name']}): {e}. Please answer from your own knowledge."

            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # Max iterations — ask for final answer without tools
    llm_no_tools = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=1500,
    )
    final = llm_no_tools.invoke(messages)
    return final.content or "Sorry, I could not process your request."
