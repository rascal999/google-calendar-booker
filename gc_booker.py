#!/usr/bin/env python3

from __future__ import print_function
import argparse
import configparser
import datetime
import os.path
import pytz
import re
import requests
import signal
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Update the SCOPES variable to include event creation permissions
SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_jira_config(config_file):
    """Load Jira configuration from a file."""
    config = configparser.ConfigParser()
    config.read(config_file)

    jira_config = {
        'BASE_URL': config.get('JIRA', 'BASE_URL').strip('\"'),
        'API_TOKEN': config.get('JIRA', 'API_TOKEN').strip('\"'),
        'EMAIL': config.get('JIRA', 'EMAIL').strip('\"')
    }

    return jira_config

def authenticate_google(config_file):
    """Authenticate and return the Google Calendar API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_calendar_timezone(service):
    """Retrieve the time zone setting of the Google Calendar."""
    settings = service.settings().get(setting='timezone').execute()
    return settings['value']

def get_jira_ticket_title(jira_config,jira_key):
    """Fetch the title of the Jira ticket using Jira API."""
    url = f"{jira_config['BASE_URL']}/rest/api/3/issue/{jira_key}"
    auth = (jira_config['EMAIL'], jira_config['API_TOKEN'])
    headers = {
        "Accept": "application/json"
    }

    response = requests.get(url, auth=auth, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data['fields']['summary']
    else:
        print(f"Failed to fetch Jira issue title for {jira_key}. Status code: {response.status_code}")
        return None

def get_free_slots(service, email_addresses, calendar_timezone, min_slots=5):
    """Return a list of at least 5 free 30-minute slots on weekdays for the given email addresses.
    A day is only considered free if the first email address doesn't have more than five hours of meetings that day."""

    tz = pytz.timezone(calendar_timezone)
    local_now = datetime.datetime.now(tz).replace(tzinfo=None)  # Remove timezone info to make it naive
    weekdays = [0, 1, 2, 3, 4]  # Monday to Friday
    first_email = email_addresses[0]

    free_slots = []
    day_offset = 0

    while len(free_slots) < min_slots:
        check_date = local_now + datetime.timedelta(days=day_offset)
        if check_date.weekday() not in weekdays:
            day_offset += 1
            continue  # Skip weekends

        # Ensure the check_date is naive before applying the timezone
        start_of_day = tz.localize(check_date.replace(hour=9, minute=0, second=0, microsecond=0))
        end_of_day = tz.localize(check_date.replace(hour=17, minute=0, second=0, microsecond=0))

        # Prepare the items list for all email addresses
        items = [{"id": email} for email in email_addresses]

        events_result = service.freebusy().query(
            body={
                "timeMin": start_of_day.isoformat(),
                "timeMax": end_of_day.isoformat(),
                "items": items
            }
        ).execute()

        # Calculate total meeting time for the first email
        total_meeting_time = datetime.timedelta()
        for busy in events_result['calendars'][first_email]['busy']:
            start = tz.normalize(datetime.datetime.fromisoformat(busy['start'][:-1]).replace(tzinfo=pytz.utc).astimezone(tz))
            end = tz.normalize(datetime.datetime.fromisoformat(busy['end'][:-1]).replace(tzinfo=pytz.utc).astimezone(tz))
            total_meeting_time += (end - start)

        # Skip the day if total meeting time exceeds 5 hours
        if total_meeting_time > datetime.timedelta(hours=5):
            day_offset += 1
            continue

        # Combine all busy intervals from all email addresses
        busy_times = []
        for email in email_addresses:
            busy_times.extend(events_result['calendars'][email]['busy'])

        # Convert busy times to datetime objects in the calendar's timezone
        busy_intervals = [
            (
                tz.normalize(datetime.datetime.fromisoformat(busy['start'][:-1]).replace(tzinfo=pytz.utc).astimezone(tz)),
                tz.normalize(datetime.datetime.fromisoformat(busy['end'][:-1]).replace(tzinfo=pytz.utc).astimezone(tz))
            )
            for busy in busy_times
        ]

        # Create a list of all 30-minute slots during the day, excluding 11:00-13:00
        current_time = start_of_day
        while current_time + datetime.timedelta(minutes=30) <= end_of_day:
            slot_start = current_time
            slot_end = slot_start + datetime.timedelta(minutes=30)

            # Skip slots that fall between 11:00 and 13:00
            if slot_start.hour >= 11 and slot_end.hour < 13:
                current_time = slot_end
                continue

            # Skip slots that are in the past
            if slot_start < tz.normalize(datetime.datetime.now(tz)):
                current_time = slot_end
                continue

            # Check if the slot is free
            slot_is_free = all(
                not (slot_start < busy_end and slot_end > busy_start)
                for busy_start, busy_end in busy_intervals
            )

            if slot_is_free:
                free_slots.append((slot_start, slot_end))

            current_time += datetime.timedelta(minutes=30)

        day_offset += 1  # Move to the next day

    return free_slots[:min_slots]

def extract_jira_key(meeting_name):
    """Extract the Jira key if it is at the start of the meeting name."""
    match = re.match(r'^([A-Z]+-\d+)', meeting_name)
    return match.group(1) if match else None

def book_meeting(jira_config, service, email_addresses, slot_start, slot_end, meeting_name, offset_minutes):
    """Book a meeting in the given time slot with an offset, and update the title with Jira key and issue title."""
    slot_start = slot_start + datetime.timedelta(minutes=offset_minutes)
    slot_end = slot_end + datetime.timedelta(minutes=offset_minutes)

    jira_key = extract_jira_key(meeting_name)
    description = f"Meeting: {meeting_name}"

    if jira_key:
        jira_title = get_jira_ticket_title(jira_config,jira_key)
        if jira_title:
            # Update the meeting name to Jira key followed by the ticket title
            meeting_name = f"{jira_key} - {jira_title}"
            jira_url = f"https://mangopay.atlassian.net/browse/{jira_key}"
            description = f"{jira_url}\n\n{description}"

    print(slot_start.isoformat())
    event = {
        'summary': meeting_name,
        'description': description,
        'start': {
            'dateTime': slot_start.isoformat(),
            'timeZone': 'Europe/London',  # Ensure meeting is booked in the calendar's timezone
        },
        'end': {
            'dateTime': slot_end.isoformat(),
            'timeZone': 'Europe/London',  # Ensure meeting is booked in the calendar's timezone
        },
        'attendees': [{'email': email} for email in email_addresses],
        'reminders': {
            'useDefault': True
        },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Meeting booked: {event.get('htmlLink')}")

def parse_arguments():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description='Schedule a Google Calendar meeting with Jira integration.')
    parser.add_argument('--emails', nargs='+', required=True, help='List of email addresses to invite.')
    parser.add_argument('--title', required=True, help='Meeting title. Will use ticket title if Jira key specified.')
    parser.add_argument('--offset', type=int, default=0, help='Offset in minutes for the meeting time.')
    parser.add_argument('--jira-creds', help='Path to the Jira configuration file.', default='config.ini')
    parser.add_argument('--google-creds', help='Path to the Jira configuration file.', default='/etc/credentials-google')

    return parser.parse_args()

def handle_interrupt(signal, frame):
    """Handle the Ctrl+C signal gracefully."""
    print("\nProcess interrupted by user. Exiting...")
    sys.exit(0)

if __name__ == '__main__':
    # Setup signal handler for Ctrl+C
    signal.signal(signal.SIGINT, handle_interrupt)

    args = parse_arguments()

    # Load Jira configuration
    jira_config = load_jira_config(args.jira_creds)

    service = authenticate_google(args.google_creds)

    # Get the calendar's timezone
    calendar_timezone = get_calendar_timezone(service)
    print(f"Calendar time zone: {calendar_timezone}")

    # Get the list of free slots
    free_slots = get_free_slots(service, args.emails, calendar_timezone)

    if not free_slots:
        print("No free slots available.")
    else:
        print("Available free slots:")
        for i, (start, end) in enumerate(free_slots):
            print(f"{i + 1}: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%H:%M')}")

        try:
            # Let user choose a slot
            slot_choice = int(input("Select a slot by number: ")) - 1

            if slot_choice < 0 or slot_choice >= len(free_slots):
                print("Invalid choice.")
            else:
                slot_start, slot_end = free_slots[slot_choice]
                #import pdb; pdb.set_trace()

                # The meeting name is the Jira key
                meeting_name = args.title

                # Book the meeting with the selected slot and offset
                book_meeting(jira_config, service, args.emails, slot_start, slot_end, meeting_name, args.offset)
        except ValueError:
            print("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            handle_interrupt(None, None)
