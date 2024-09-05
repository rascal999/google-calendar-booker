#!/usr/bin/env python3

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Authenticate using your Google Calendar credentials (assuming credentials are already handled)
# Make sure the 'token.json' exists from the OAuth flow or provide a valid credentials path
creds = Credentials.from_authorized_user_file('token.json')

# Build the service
service = build('calendar', 'v3', credentials=creds)

# Fetch the available colors
colors = service.colors().get().execute()

# Print the available event colors and their IDs
print("Event Colors:")
for color_id, color_info in colors['event'].items():
    print(f"Color ID: {color_id}, Background: {color_info['background']}, Foreground: {color_info['foreground']}")
