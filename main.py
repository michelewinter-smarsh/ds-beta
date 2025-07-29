from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from tools import bribery_playbook
from dotenv import load_dotenv
import streamlit as st
import json

MODEL = "claude-4-sonnet-20250514"  # Default model

load_dotenv()

client = Anthropic()


def handle_model_response(response):
    # Check if the response contains tool use
    if hasattr(response, 'content'):
        for content_block in response.content:
            if content_block.type == "tool_use":
                function_call = content_block.name
                arguments = content_block.input
                if function_call == "bribery_playbook":
                    db_results = bribery_playbook(**arguments)
                    
                    # Continue the conversation with the tool result
                    follow_up_response = client.messages.create(
                        model=MODEL,
                        max_tokens=4000,
                        messages=[
                            {"role": "user", "content": "Please analyze the bribery-related information I'm about to provide."},
                            {"role": "assistant", "content": response.content},
                            {
                                "role": "user", 
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": json.dumps(db_results)
                                    }
                                ]
                            }
                        ],
                        tools=[
                            {
                                "name": "bribery_playbook",
                                "description": "Query the database for bribery related information on policy, transactions, and communications between two individuals of interest.",
                                "input_schema": {
                                    "type": "object",
                                    "properties": {
                                        "user1": {"type": "string", "description": "The first user to query."},
                                        "user2": {"type": "string", "description": "The second user to query."},
                                        "collection_name": {"type": "string", "description": "The name of the collection to query."},
                                    },
                                    "required": ["user1", "user2", "collection_name"],
                                },
                            }
                        ],
                    )
                    return follow_up_response
            
            elif content_block.type == "text":
                print("Model Response: ", content_block.text)
                return content_block.text
    
    # If no tool use, return the text content
    if hasattr(response, 'content') and response.content:
        for content_block in response.content:
            if content_block.type == "text":
                return content_block.text
    
    return response


def main(input_query):
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[
            {"role": "user", "content": input_query}
        ],
    )

    next_response = handle_model_response(response)

    # Handle different response types
    if isinstance(next_response, str):
        return next_response
    elif hasattr(next_response, 'content'):
        for content_block in next_response.content:
            if content_block.type == "text":
                return content_block.text
    
    return str(next_response)


if __name__ == "__main__":

    prompt = "Investigate Jho Low's communications for money laundering."

    reply = main(prompt)
