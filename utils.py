"""
Utility functions.
"""
import re
from datetime import datetime

def parse_email(raw_email):
    lines = raw_email.splitlines()
    email_data = {
        "sender": None,
        "receiver": None,
        "subject": None,
        "body": "",
        "timestamp": None
    }

    body_started = False
    body_lines = []

    for line in lines:
        line = line.strip()
        if not line and not body_started:
            body_started = True
            continue
        if body_started:
            body_lines.append(line)
        elif line.lower().startswith("from:"):
            match = re.search(r'<([^>]+)>', line)
            email_data["sender"] = match.group(1) if match else line[5:].strip()
        elif line.lower().startswith("to:"):
            match = re.search(r'<([^>]+)>', line)
            email_data["receiver"] = match.group(1) if match else line[3:].strip()
        elif line.lower().startswith("subject:"):
            email_data["subject"] = line[8:].strip()
        elif line.lower().startswith("date:"):
            date_str = line[5:].strip()
            # optional: parse to datetime object
            try:
                email_data["timestamp"] = datetime.strptime(
                    date_str, "%a, %d %b %Y %H:%M:%S %z (%Z)"
                )
            except ValueError:
                email_data["timestamp"] = date_str  # fallback to raw string

    email_data["body"] = "\n".join(body_lines).strip()
    return email_data
