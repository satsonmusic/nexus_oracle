from app.tools.calendar import create_event, list_upcoming_events
from app.tools.gmail import send_email, read_recent_emails

TOOLS = {
    "create_event": create_event,
    "list_upcoming_events": list_upcoming_events,
    "send_email": send_email,
    "read_recent_emails": read_recent_emails
}
# Keep your existing imports up here...
from app.tools.calendar import create_event, list_upcoming_events
# ... your email imports ...

# ADD THIS LINE:
from app.tools.web_search import search_internet

TOOLS = {
    # ... your existing tools ...
    "list_upcoming_events": list_upcoming_events,
    "create_event": create_event,
    
    # ADD THIS LINE:
    "search_internet": search_internet
}
# ADD THIS LINE:
from app.tools.chat import respond_to_user

TOOLS = {
    "list_upcoming_events": list_upcoming_events,
    "create_event": create_event,
    "search_internet": search_internet,
    
    # ADD THIS LINE:
    "respond_to_user": respond_to_user,
    # ... your email tools ...
}