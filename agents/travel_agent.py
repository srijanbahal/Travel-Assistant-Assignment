from langchain_classic.agents import create_tool_calling_agent
from langchain_classic.agents.agent import AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tools.flights import search_flights
from tools.hotels import search_hotels
from tools.trains import search_trains, search_buses
from agents.llm_engine import get_llm
from agents.a2a_schema import A2AMessage

tools = [search_flights, search_hotels, search_trains, search_buses]
llm = get_llm()

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful travel assistant. Use the provided tools to search for flights, hotels, trains, and buses. "
               "When you find results, summarize them clearly for the user. "
               "If no results are found, suggest alternatives or ask for more details. "
               "Always include prices and key details."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
travel_agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def run_travel_agent(input_msg: A2AMessage, chat_history: list) -> A2AMessage:
    response = travel_agent_executor.invoke({
        "input": input_msg.content,
        "chat_history": chat_history
    })
    output_content = response['output']
    
    # Handle list content (e.g. from Gemini/LangChain update)
    if isinstance(output_content, list):
        text_parts = []
        for block in output_content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(block["text"])
            elif isinstance(block, str):
                text_parts.append(block)
        output_content = " ".join(text_parts)
    
    return A2AMessage(
        sender="TravelAgent",
        receiver="TranslationAgent",
        message_type="RESPONSE",
        content=str(output_content),
        context={}
    )
