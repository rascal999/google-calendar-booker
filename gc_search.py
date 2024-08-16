#!/usr/bin/env python3

import os
import argparse
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def authenticate_google_calendar():
    """Authenticate and return the Google Calendar service."""
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def search_meetings_by_title(calendar_service, partial_title):
    """Search for meetings by partial title and return details including attendees."""
    # Define the time range for searching (e.g., next 7 days)
    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    end_time = (datetime.datetime.utcnow() + datetime.timedelta(days=93)).isoformat() + 'Z'

    # Call the Calendar API
    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=now,
        timeMax=end_time,
        q=partial_title,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    if not events:
        print(f'No upcoming meetings found with the title containing "{partial_title}".')
        return

    print(f'Upcoming meetings with the title containing "{partial_title}":')
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        print(f'{start} - {event["summary"]}')

        # Print attendees and their status
        if 'attendees' in event:
            print("Attendees:")
            for attendee in event['attendees']:
                email = attendee.get('email')
                response_status = attendee.get('responseStatus')
                print(f" - {email} ({response_status})")
        else:
            print("No attendees listed.")
        print()

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Search for meetings in Google Calendar by partial title.')
    parser.add_argument('search_term', type=str, help='Partial title of the meeting to search for')

    args = parser.parse_args()

    # Authenticate and search for meetings
    calendar_service = authenticate_google_calendar()
    search_meetings_by_title(calendar_service, args.search_term)

if __name__ == '__main__':
    main()
