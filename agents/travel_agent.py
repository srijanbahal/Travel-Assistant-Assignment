from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from tools.flights import search_flights
from tools.hotels import search_hotels
from tools.trains import search_trains, search_buses
from agents.llm_engine import get_llm

tools = [search_flights, search_hotels, search_trains, search_buses]
llm = get_llm()

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. Use the provided tools to search for flights, hotels, trains, and buses. "
               "When you find results, summarize them clearly for the user. "
               "If no results are found, suggest alternatives or ask for more details. "
               "Always include prices and key details."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
travel_agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
