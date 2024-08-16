#!/usr/bin/env python3

import argparse
import configparser
import logging
from jira import JIRA
from jira.exceptions import JIRAError

def get_jira_connection(jira_url, username, api_token):
    """
    Connect to Jira.

    :param jira_url: The base URL of the Jira instance (e.g., "https://your-domain.atlassian.net")
    :param username: The Jira username or email address used for authentication
    :param api_token: The API token for Jira authentication
    :return: JIRA connection object
    """
    try:
        jira = JIRA(basic_auth=(username, api_token), server=jira_url)
        logging.debug(f"Connected to Jira at {jira_url}")
        return jira
    except JIRAError as e:
        logging.error(f"Failed to connect to Jira: {str(e)}")
        return None

def get_epic_issues(jira, epic_ticket_id, issue_type):
    """
    Get all issues of a specific type linked to the given Epic.

    :param jira: JIRA connection object
    :param epic_ticket_id: The Epic Jira ticket ID (e.g., "TICKET-1")
    :param issue_type: The type of issues to filter (e.g., "Security Review")
    :return: List of issue keys that match the issue type and are linked to the Epic
    """
    try:
        # Search for all issues linked to the Epic
        jql_query = f'"Epic Link" = {epic_ticket_id} AND issuetype = "{issue_type}"'
        logging.debug(f"JQL Query: {jql_query}")

        issues = jira.search_issues(jql_query)
        logging.debug(f"Found {len(issues)} issues linked to Epic {epic_ticket_id} of type '{issue_type}'")

        return [issue.key for issue in issues]

    except JIRAError as e:
        logging.error(f"Failed to retrieve issues linked to Epic: {str(e)}")
        return []

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
    parser = argparse.ArgumentParser(description='Get all issues of a specific type linked to a Jira Epic.')
    parser.add_argument('epic_ticket_id', type=str, help='The Jira Epic ticket ID (e.g., "TICKET-1")')
    parser.add_argument('--issue-type', type=str, required=True, help='The issue type to filter (e.g., "Security Review")')
    parser.add_argument('--config', type=str, default='config.ini', help='Path to the config.ini file')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')

    args = parser.parse_args()

    # Set logging level based on --debug flag
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.debug("Debug mode is enabled.")
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug(f"Arguments received: epic_ticket_id='{args.epic_ticket_id}', issue_type='{args.issue_type}', config='{args.config}'")

    # Load Jira configuration from config file
    jira_config = load_jira_config(args.config)

    # Connect to Jira
    jira = get_jira_connection(jira_config['jira_url'], jira_config['username'], jira_config['api_token'])
    if jira is None:
        print("Failed to connect to Jira.")
        return

    # Get issues linked to the Epic of the specified type
    epic_issues = get_epic_issues(jira, args.epic_ticket_id, args.issue_type)

    if epic_issues:
        #print(f"Issues of type '{args.issue_type}' linked to Epic {args.epic_ticket_id}:")
        for issue_key in epic_issues:
            print(issue_key)
    else:
        print(f"No issues of type '{args.issue_type}' found for Epic {args.epic_ticket_id}.")

if __name__ == "__main__":
    main()
