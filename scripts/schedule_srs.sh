#!/usr/bin/env bash

if [[ "$#" -ne "1" ]]; then
    echo "ERROR: Ticket not specified."
    exit 1
fi

WORK_EMAIL=`cat work-email.txt`

# Given epic, fetch reporter email
EMAIL_REPORTER=`scripts/jira_reporter.py $1`

if [[ "$?" -ne "0" ]]; then
    echo "Couldn't find email for $1"
    exit 1
fi

# Given epic, fetch ticket ID for Security Review
SR=`scripts/jira_fetch_children.py --issue-type "Security Review" $1`

# Given ticket ID of SR and epic reporter email, schedule meeting
./gc_booker.py --emails ${WORK_EMAIL} ${EMAIL_REPORTER} --title "${SR}"
