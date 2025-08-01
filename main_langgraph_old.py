from dotenv import load_dotenv

from typing import Annotated

from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()
# This is the in-memory checkpointer.
# In production change this to use SqliteSaver or PostgresSaver and connect a database.

load_dotenv()

MODEL = "claude-4-sonnet-20250514"  # Default model

config = {"configurable": {"thread_id": "1"}}


class State(TypedDict):
    messages: Annotated[list, add_messages]

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    context: str  # Store context in state
    email_data: dict  # Store structured data

def add_context_node(state: ChatState):
    """Add context before the chat model processes"""
    context = state.get("context", "")
    email_data = state.get("email_data", {})
    
    # Format context message
    context_message = f"""
    CONTEXT: {context}
    
    EMAIL DATA:
    {format_email_data(email_data)}
    
    Please analyze the following query in light of this context.
    """
    
    # Add context as a system-like message
    current_messages = state["messages"]
    if current_messages and not any("CONTEXT:" in str(msg) for msg in current_messages):
        context_msg = {"role": "user", "content": context_message}
        return {"messages": [context_msg] + current_messages}
    
    return {"messages": current_messages}


llm = init_chat_model(MODEL, temperature=0.2, max_tokens=1000).bind(
    system="You are an expert email analyst working for a financial services company. "
           "You have access to internal communications and should analyze them for "
           "compliance issues and sentiment. Always cite specific "
           "email references when making claims.")


def chatbot(state: State):
    return {"messages": [llm.invoke(state["messages"])]}


# The first argument is the unique node name
# The second argument is the function or object that will be called whenever
# the node is used.
graph_builder = StateGraph(State)
graph_builder.add_node("add_context", add_context_node)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge("add_context", "chatbot")
graph_builder.add_edge("chatbot", END)
graph_builder.set_entry_point("add_context")
graph = graph_builder.compile(checkpointer=memory)


def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}, config, stream_mode='values'):
        # Only print if the last message is from the assistant
        last_message = event["messages"][-1]
        if hasattr(last_message, 'type') and last_message.type == 'ai':
            print("LLM: " + last_message.content)


while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What's the weather like today?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break