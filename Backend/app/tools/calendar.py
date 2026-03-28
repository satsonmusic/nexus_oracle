import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
# Change it to this:
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://mail.google.com/'
]

def get_calendar_service():
    """Handles Google OAuth and returns the Calendar service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # You must have a credentials.json file from Google Cloud Console in your root folder
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('calendar', 'v3', credentials=creds)

def create_event(title: str, start_time: str, end_time: str, description: str = "") -> str:
    """
    Creates an event in the user's primary calendar.
    Time format expected from LLM: ISO 8601 (e.g., '2026-03-25T09:00:00-05:00')
    """
    try:
        service = get_calendar_service()
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC', # The LLM should ideally calculate timezone offsets, or you can hardcode yours here
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return f"Success! Event created: {event_result.get('htmlLink')}"
    except Exception as e:
        return f"Failed to create event: {str(e)}"

def list_upcoming_events(max_results: int = 10) -> str:
    """Lists the user's upcoming events so Jarvis can check your schedule."""
    try:
        service = get_calendar_service()
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=max_results, singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."

        res = []
        for event in events:
            # Grab the start time (handles both all-day and specific-time events)
            start = event['start'].get('dateTime', event['start'].get('date'))
            res.append(f"[{start}] {event['summary']}")
            
        return "Upcoming Schedule:\n" + "\n".join(res)
    except Exception as e:
        return f"Failed to fetch events: {str(e)}"