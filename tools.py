"""
Tool functions for the DeepSearch project.

"""
import pandas as pd
import pickle as p


def load_all_emails():
    """
    Load all emails from the database.
    """
    return pd.read_excel("generated_emails_with_background_7.xlsx").to_dict(orient="records")

def load_participant_descriptions():
    """
    Load participant descriptions from the database.
    """
    with open("participant_descriptions.pkl", "rb") as f:
        return p.load(f)


def filter_emails_by_person(all_emails, poi_email_address):
    """
    Filter emails by person of interest.
    """
    # all_emails = load_all_emails()
    filtered_emails = [email for email in all_emails if email["sender"] == poi_email_address or poi_email_address in email["recipients"]]
    return filtered_emails
