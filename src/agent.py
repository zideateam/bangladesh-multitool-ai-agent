"""Main LangChain AgentExecutor for Bangladesh dataset and web queries."""
from __future__ import annotations

import os

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an evidence-grounded Bangladesh multi-tool assistant.
Route institution-record queries to InstitutionsDBTool, healthcare-facility-record
queries to HospitalsDBTool, restaurant-record queries to RestaurantsDBTool,
and general policy/definition/current queries to WebSearchTool. Use more than
one tool if necessary. Always retrieve before stating dataset counts.
Use only SELECT and actual columns (inspect the schema printed in setup).
SQL tables: institutions, hospitals, restaurants. Use LOWER() for text matching.
The hospitals data includes healthcare facilities beyond hospitals; the source
does not provide verified hospital bed counts, numbers of doctors, or services.
The restaurant data lacks verified cuisine types. Do not invent missing fields.
Web results are not inherently verified: cite the source URLs and distinguish
policy dates from current policy updates. No data modifications. When results
are absent or a tool errors, explain limitations and do not make up answers.
"""


def create_executor(model: str = "gpt-4.1-mini") -> AgentExecutor:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Configure OPENAI_API_KEY before creating the agent.")
    model_client = ChatOpenAI(model=model, temperature=0, max_retries=2)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(model_client, ALL_TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=ALL_TOOLS, verbose=True,
                         return_intermediate_steps=True, max_iterations=5,
                         handle_parsing_errors=True)
