#!/usr/bin/env python3

import argparse
import configparser
import logging
import sys
from jira import JIRA
from jira.exceptions import JIRAError

def get_ticket_reporter_email(ticket_id, jira_url, username, api_token):
    """
    Get the email address of the reporter for a given Jira ticket ID.

    :param ticket_id: The Jira ticket ID (e.g., "PROJECT-123")
    :param jira_url: The base URL of the Jira instance (e.g., "https://your-domain.atlassian.net")
    :param username: The Jira username or email address used for authentication
    :param api_token: The API token for Jira authentication
    :return: The email address of the ticket reporter
    """
    try:
        # Connect to Jira
        jira = JIRA(basic_auth=(username, api_token), server=jira_url)
        logging.debug(f"Connected to Jira at {jira_url}")

        # Get the issue details
        issue = jira.issue(ticket_id)
        logging.debug(f"Issue details retrieved for ticket ID: {ticket_id}")

        # Get the reporter's email address
        reporter_email = issue.fields.reporter.emailAddress
        logging.debug(f"Reporter email: {reporter_email}")

        return reporter_email

    except JIRAError as e:
        logging.error(f"Failed to retrieve reporter email: {str(e)}")
        return None

def load_jira_config(config_file):
    """
    Load Jira configuration from the specified config file.

    :param config_file: Path to the config.ini file
    :return: A dictionary containing Jira configuration
    """
    config = configparser.ConfigParser()
    config.read(config_file)

    jira_config = {
        'jira_url': config.get('JIRA', 'BASE_URL').strip("\""),
        'username': config.get('JIRA', 'EMAIL').strip("\""),
        'api_token': config.get('JIRA', 'API_TOKEN').strip("\"")
    }

    logging.debug(f"Jira configuration loaded: {jira_config}")
    return jira_config

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Get the email address of the reporter for a Jira ticket.')
    parser.add_argument('ticket_id', type=str, help='The Jira ticket ID (e.g., "PROJECT-123")')
    parser.add_argument('--config', type=str, default='config.ini', help='Path to the config.ini file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    # Set logging level based on --debug flag
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.debug("Debug mode is enabled.")
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug(f"Arguments received: ticket_id='{args.ticket_id}', config='{args.config}'")

    # Load Jira configuration from config file
    jira_config = load_jira_config(args.config)

    # Get the reporter's email address
    reporter_email = get_ticket_reporter_email(args.ticket_id, jira_config['jira_url'], jira_config['username'], jira_config['api_token'])

    if reporter_email:
        print(f"{reporter_email}")
        sys.exit(0)
    else:
        print("Failed to retrieve the reporter's email address.")
        sys.exit(1)

if __name__ == "__main__":
    main()
