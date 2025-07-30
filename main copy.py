from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from tools import load_all_emails, load_participant_descriptions, filter_emails_by_person
from dotenv import load_dotenv
import streamlit as st
import json
from datetime import datetime
import time

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
                            {
                                "role": "user",
                                "content": "Please analyze the bribery-related information I'm about to provide.",
                            },
                            {"role": "assistant", "content": response.content},
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": content_block.id,
                                        "content": json.dumps(db_results),
                                    }
                                ],
                            },
                        ],
                        tools=[
                            {
                                "name": "bribery_playbook",
                                "description": (
                                    "Query the database for bribery related information on policy, transactions, and communications between two individuals of interest."
                                ),
                                "input_schema": {
                                    "type": "object",
                                    "properties": {
                                        "user1": {"type": "string", "description": "The first user to query."},
                                        "user2": {"type": "string", "description": "The second user to query."},
                                        "collection_name": {
                                            "type": "string",
                                            "description": "The name of the collection to query.",
                                        },
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


def main(input_query, context=None):
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system="You are an expert investigator specializing in financial misconduct such as bribery, money laundering and corruption. Your task is to analyze communications for signs of illicit activities and extract necessary information such as secondary people of interest, entities, and events that are necessary to build a case.",
        messages=[{"role": "user", "content": input_query}], 
    )
    # TODO: Dial down temperature to 0.2-0.3 for more factual responses
    # TODO: Can make system prompt more instructive. Can add delimiters - only the text between "start, end".
    # Can force it ot rank things - oneshot examples. Based on how likely you think it is to be connected. For example: ex.
    # Can run a subsequent pass to specifically check results of first prompt
        # Can run second prompt where validate that content in first findings are in this message.
    # TODO: Add langchain. version 2. Latest. 'with structured output'
    # Define a pydantic model. Pass references model as well (saves tokens).
    # TonicAI has frameworks for validation.
    # Some tooling for basic checks/tests. Validate output of models against what I'm expecting.
    # TODO: [Validation] The network is very programmatically accessible. If we know network, then we have a structure that we can assert against the model's output.
    # TODO: Parse the email data for the emails, saying John messaged Rudi at this time, might at coherence to the story, might also add noise.
    # Instead of giving metadata, could build metadata into the prompt with more direction. 
        # Test option: Maybe instead of passing email raw, change email to "On Sunday, Jho Low sent an email to Najib Razak with the subject 'Request for Transfer from GS' at 3:00 PM. The email contained the following text: 'Please transfer $1 million to my account.' and this might be easier for the model to understand - would be interesting to see the results of this.
    # TODO: How am I defining entity? Define in the schema in the pydantic description.
    # TODO: Add realistic times that people sent the emails. Currently they are all sent at 12:00 AM.
    # TODO: In the financial industry, the definition of these things (bribery, money laundering, corruption), and give these definition to the model.


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

    user_prompt = """ 
            You are investigating Jho Low's communications for suspicious financial activity.
            None of this is information is related to the actual 1MDB case, but is a test of your ability to read and understand emails. Do not use any of your prior information about Jho Low or 1MDB to answer the questions. After reading Jho Low's emails, please list the following that you found in the emails: 
            - Secondary people of interest
            - Key events
            - Suspicious activities
            - Entities of note (such as companies, organizations, or other entities involved in the communications).
            
            Return what you find as a JSON response with this structure: 
            {
                "secondary_poi": {
                    "name": "John Doe",
                    "email_address": "john.doe@example.com",
                    "description": "Description of the person and relationship to Jho Low",
                    "reasoning": "Description of why this person is of interest",
                    "references": [{
                        "email_id": "Unique identifier ID for the email where this person was mentioned. Under key 'id'.",
                        "email_subject": "List of email subjects where this person was mentioned.",
                        "quotes": "List of quotes from the email where this person was mentioned.",
                        "description": "Couple sentence description of why this email is relevant to the case.",
                        },
                    ],
                },
                "key_events": {
                    "event": "Description of the event",
                    "date": "Date of the event",
                    "location": "Location of the event",
                    "references": [{
                        "email_id": "Unique identifier ID for the email where this event was mentioned. Under key 'id'.",
                        "email_subject": "List of email subjects where this event was mentioned.",
                        "quotes": "List of quotes from the email where this event was mentioned.",
                        "description": "Couple sentence description of why this email is relevant to the case.",
                        },
                    ],
                },
                "sus_activities": {
                    "short_title": "Short title of the activity",
                    "description": "Description of the activity",
                    "date": "Date of the activity",
                    "references": [{
                        "email_id": "Unique identifier ID for the email where this activity was mentioned. Under key 'id'.",
                        "email_subject": "List of email subjects where this activity was mentioned.",
                        "quotes": "List of quotes from the email where this activity was mentioned.",
                        "description": "Couple sentence description of why this email is relevant to the case.",
                        },
                    ],
                },
                "entities_of_note": [
                    {
                        "name": "Company Name",
                        "type": "Type of entity (e.g., company, organization)",
                        "description": "Description of the entity and its relevance to the case",
                        "references": [{
                            "email_id": "Unique identifier ID for the email where this entity was mentioned. Under key 'id'.",
                            "email_subject": "List of email subjects where this entity was mentioned.",
                            "quotes": "List of quotes from the email where this entity was mentioned.",
                            "description": "Couple sentence description of why this email is relevant to the case.",
                            },
                        ],
                    }
                ]
            }

            After your analysis, please answer these verification questions:
            1. How many emails did I provide for analysis? List their email ID numbers.
            3. What specific time was mentioned in the 'Request for Transfer from GS' email?
            4. If I ask about information not in these emails, what should your response be?
            """
    emails = load_all_emails()
    participant_descriptions = load_participant_descriptions()

    jlow_email_address = [
        entry['email_address'] for entry in participant_descriptions if entry['participant'] == "Jho Low"
    ][0]
    for i, email in enumerate(emails):
        email['email_id'] = f'EMAIL_{i+2}'
    emails = filter_emails_by_person(emails, jlow_email_address)
    # TODO: Play around with batch size, start at one at a time, etc

    # Add unique IDs to emails
    import ipdb; ipdb.set_trace()
    combined_prompt = f"""
    Prompt: {user_prompt}\n
    Context: {emails}
    """
    start_time = time.time()
    reply = main(combined_prompt)
    end_time = time.time()
    print(f"LLM processing time: {end_time - start_time:.2f} seconds")

    print("Final Response: ", reply)

    # Save the response as a JSON file
    try:
        # Extract JSON from markdown code blocks if present
        json_content = reply
        if "```json" in reply:
            # Find JSON content
            start_marker = "```json"
            end_marker = "```"
            start_index = reply.find(start_marker) + len(start_marker)
            end_index = reply.find(end_marker, start_index)
            if end_index != -1:
                json_content = reply[start_index:end_index].strip()
        elif "```" in reply:
            # Handle generic code blocks
            start_index = reply.find("```") + 3
            end_index = reply.find("```", start_index)
            if end_index != -1:
                json_content = reply[start_index:end_index].strip()

        # Parse and save
        reply_json = json.loads(json_content)
        with open(f"investigation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(reply_json, f, indent=2)
        print(f"Results saved to investigation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        # If the reply isn't valid JSON, save it as a text file instead
        with open(f"investigation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
            f.write(reply)
        print(
            f"Results saved to investigation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt (not valid JSON)"
        )
