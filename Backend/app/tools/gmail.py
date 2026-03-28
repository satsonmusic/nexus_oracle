import os
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Notice we are asking for BOTH Calendar and Gmail access now
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://mail.google.com/'
]

def get_gmail_service():
    """Handles Google OAuth and returns the Gmail service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def send_email(to_email: str, subject: str, body: str) -> str:
    """Sends an email using the Gmail API."""
    try:
        service = get_gmail_service()
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject

        # Gmail API requires URL-safe base64 encoding
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}

        send_message = service.users().messages().send(userId='me', body=create_message).execute()
        return f"Success! Email sent to {to_email}. Message ID: {send_message['id']}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

def read_recent_emails(max_results: int = 5) -> str:
    """Reads the subjects and senders of recent emails."""
    try:
        service = get_gmail_service()
        # Fetch the most recent emails from the INBOX
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return "Inbox is empty or no recent emails found."

        output = []
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload.get('headers', [])
            
            # Extract Subject and Sender
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            
            output.append(f"- From: {sender} | Subject: {subject}")

        return "Recent Emails:\n" + "\n".join(output)
    except Exception as e:
        return f"Failed to read emails: {str(e)}"