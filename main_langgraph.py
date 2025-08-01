from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, StructuredChatAgent
from pydantic import BaseModel, Field
from tools import load_all_emails, load_participant_descriptions, filter_emails_by_person
from typing import Annotated, TypedDict, List, Optional
from langchain_core.tools import tool
import json

# from langchain.agents.output_parsers import ToolsAgentOutputParser
from langchain.prompts import ChatPromptTemplate

load_dotenv()
# MODEL = "claude-4-sonnet-20250514"  # Default model
MODEL = "bedrock_converse:us.anthropic.claude-sonnet-4-20250514-v1:0"

config = {"configurable": {"thread_id": "1"}}


class Reference(BaseModel):
    """Reference to an email with context"""

    email_id: str = Field(description="Unique identifier for the email")
    email_subject: str = Field(description="Subject of the email")
    quotes: str = Field(description="Relevant quotes from the email")
    description: str = Field(description="Description of why this email is relevant to the case")


class Entity(BaseModel):
    name: str
    type: str
    description: str
    references: List[Reference]


class SecondaryPOI(BaseModel):
    name: str
    email_address: str
    description: str
    reasoning: str
    references: List[Reference]


class KeyEvent(BaseModel):
    event: str
    date: str
    location: str
    references: List[Reference]


class SuspiciousActivity(BaseModel):
    short_title: str
    description: str
    date: str
    references: List[Reference]


class InvestigationResults(BaseModel):
    """Results of the investigation"""

    secondary_poi: List[SecondaryPOI] = Field(default=[], description="List of secondary people of interest")
    key_events: List[KeyEvent] = Field(default=[], description="List of key events")
    sus_activities: List[SuspiciousActivity] = Field(default=[], description="List of suspicious activities")
    entities_of_note: List[Entity] = Field(default=[], description="List of entities of note")


# # Wrap schema in a langchain tool
# @tool
# def produce_investigation_results(text: str) -> InvestigationResults:
#     """Formats the investigation results."""
#     pass  # dummy tool


# Define the state
class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
    context: str
    email_data: dict


# tools=[produce_investigation_results]

# Define system prompt
# prompt = StructuredChatAgent.create_prompt(
#     # tools=tools,
#     system_message_template="You are a helpful assistant that uses tools to extract structured data from emails."
# )
# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful assistant that can extract structured information using tools."),
#     ("human", "{input}"),
#     ("placeholder", "{agent_scratchpad}")  # required for tool-using agents
# ])
# Initialize your LLM
llm = init_chat_model(MODEL, temperature=0.2, max_tokens=1000)
# Add schema for structured output
structured_llm = llm.with_structured_output(InvestigationResults)

# Create agent with tool support
# agent = create_tool_calling_agent(llm=llm, prompt=prompt, tools=tools)
# runnable = agent | ToolsAgentOutputParser()


def add_context_node(state: ChatState):
    """Add context before the chat model processes"""
    context = state.get("context", "")
    email_data = state.get("email_data", {})

    if not context and not email_data:
        return {"messages": state["messages"]}

    # Format context message
    context_parts = []
    if context:
        context_parts.append(f"CONTEXT: {context}")

    if email_data:
        context_parts.append(f"EMAIL DATA: {format_email_data(email_data)}")

    context_message = "\n\n".join(context_parts) + "\n\nPlease analyze the following query in light of this context."

    # Add context to the first user message
    current_messages = state["messages"]
    if current_messages:
        last_message = current_messages[-1]
        # Check if it's a user message (handle both dict and LangChain message objects)
        if hasattr(last_message, 'type') and last_message.type == 'human':
            # It's a LangChain HumanMessage object
            original_content = last_message.content
            enhanced_content = f"{context_message}\n\nUSER QUERY: {original_content}"
            # Create a new message dict
            current_messages[-1] = {"role": "user", "content": enhanced_content}
        elif isinstance(last_message, dict) and last_message.get("role") == "user":
            # It's a dictionary message
            original_content = last_message["content"]
            enhanced_content = f"{context_message}\n\nUSER QUERY: {original_content}"
            current_messages[-1] = {"role": "user", "content": enhanced_content}

    return {"messages": current_messages}


def chat_node(state: ChatState):
    """Chat node that processes messages"""
    response = structured_llm.invoke(state["messages"])
    # return {"messages": [response]}
    # Convert to dict first, then to JSON
    response_dict = {
        "secondary_poi": getattr(response, 'secondary_poi', []),
        "key_events": getattr(response, 'key_events', []),
        "sus_activities": getattr(response, 'sus_activities', []),
        "entities_of_note": getattr(response, 'entities_of_note', [])
    }
    response_json = json.dumps(response_dict, indent=2, default=str)
    # except Exception as e:
    #     # Fallback to string representation
    #     response_json = f"Error serializing response: {str(e)}\nResponse type: {type(response)}\nResponse: {str(response)}"
    
    # Return as a proper message format
    return {"messages": [{"role": "assistant", "content": response_json}]}


def format_email_data(email_data: dict) -> str:
    """Helper function to format email data"""
    if not email_data:
        return "No email data provided"

    formatted = []
    for key, value in email_data.items():
        if isinstance(value, list):
            formatted.append(f"{key}: {', '.join(map(str, value))}")
        else:
            formatted.append(f"{key}: {value}")

    return "\n".join(formatted)


# Build the graph
workflow = StateGraph(ChatState)
workflow.add_node("add_context", add_context_node)
workflow.add_node("chat", chat_node)
workflow.add_edge("add_context", "chat")
workflow.set_entry_point("add_context")

# Compile the graph
graph = workflow.compile()


# Your updated streaming function
def stream_graph_updates(user_input: str, context: str = "", email_data: dict = None):
    """Stream updates with context support"""

    # Prepare the initial state with context
    initial_state = {
        "messages": [{"role": "user", "content": user_input}],
        "context": context,
        "email_data": email_data or {},
    }

    # Stream the graph execution
    for event in graph.stream(initial_state, config, stream_mode='values'):
        # Only print if the last message is from the assistant
        last_message = event["messages"][-1]
        if hasattr(last_message, 'type') and last_message.type == 'ai':
            print("LLM: " + last_message.content)


# Usage examples
if __name__ == "__main__":

    emails = load_all_emails()
    participant_descriptions = load_participant_descriptions()

    jlow_email_address = [
        entry['email_address'] for entry in participant_descriptions if entry['participant'] == "Jho Low"
    ][0]
    for i, email in enumerate(emails):
        email['email_id'] = f'EMAIL_{i+2}'
    email_data = filter_emails_by_person(emails, jlow_email_address)

    user_prompt = """ 
            You are investigating Jho Low's communications for suspicious financial activity.
            None of this is information is related to the actual 1MDB case, but is a test of your ability to read and understand emails. Do not use any of your prior information about Jho Low or 1MDB to answer the questions. After reading Jho Low's emails, please analyze them and extract the following information:
            
            1. Secondary people of interest - other individuals mentioned who warrant investigation
            2. Key events - important dates, meetings, or occurrences mentioned in the emails
            3. Suspicious activities - any potentially illegal or unethical behavior described
            4. Entities of note - companies, organizations, or other entities involved
            
            You MUST return results for ALL FOUR categories. If no information is found for a category, return an empty list for that category.
            
            Use the InvestigationResults schema format with proper references to email IDs, subjects, and quotes.
            """

    stream_graph_updates(
        user_input=user_prompt,
        context="You are an expert investigator specializing in financial misconduct such as bribery, money laundering and corruption. Your task is to analyze communications for signs of illicit activities and extract necessary information such as secondary people of interest, entities, and events that are necessary to build a case.",
        email_data=email_data[1],
    )
