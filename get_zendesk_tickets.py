"""
This script can be used to retrieve Zendesk tickets.
This can be run locally if you set the ZENDESK_API_KEY. Or the script can be run from a flask shell from a ssh session.
"""
# flake8: noqa: T001 (print)

import csv
import os
import urllib.parse

import requests

# Group: 3rd Line--Notify Support
NOTIFY_GROUP_ID = 360000036529

# Organization: GDS
NOTIFY_ORG_ID = 21891972

# the account used to authenticate with. If no requester is provided, the ticket will come from this account.
NOTIFY_ZENDESK_EMAIL = 'zd-api-notify@digital.cabinet-office.gov.uk'
ZENDESK_API_KEY = os.environ.get('ZENDESK_API_KEY')


def get_tickets():
    ZENDESK_TICKET_URL = 'https://govuk.zendesk.com/api/v2/search.json?query={}'
    query_params = 'type:ticket group:{}'.format(NOTIFY_GROUP_ID)
    query_params = urllib.parse.quote(query_params)

    next_page = ZENDESK_TICKET_URL.format(query_params)

    with open("zendesk_ticket_data.csv", 'w') as csvfile:
        fieldnames = [
            'Service id',
            'Ticket id',
            'Subject line',
            'Date ticket created',
            'Tags',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        while next_page:
            print(next_page)
            response = requests.get(
                next_page,
                headers={'Content-type': 'application/json'},
                auth=(
                    '{}/token'.format(NOTIFY_ZENDESK_EMAIL),
                    ZENDESK_API_KEY
                )
            )
            data = response.json()
            print(data)
            for row in data["results"]:
                service_url = [x for x in row["description"].split('\n')
                               if x.startswith("https://www.notifications.service.gov.uk/services/")]
                service_url = service_url[0][50:] if len(service_url) > 0 else None
                if service_url:
                    writer.writerow({'Service id': service_url,
                                     'Ticket id': row['id'],
                                     'Subject line': row['subject'],
                                     'Date ticket created': row["created_at"],
                                     'Tags': row.get('tags', '')
                                     })
            next_page = data["next_page"]


def get_tickets_without_service_id():
    ZENDESK_TICKET_URL = 'https://govuk.zendesk.com/api/v2/search.json?query={}'
    query_params = 'type:ticket group:{}'.format(NOTIFY_GROUP_ID)
    query_params = urllib.parse.quote(query_params)

    next_page = ZENDESK_TICKET_URL.format(query_params)
    with open("zendesk_ticket_data_without_service.csv", 'w') as csvfile:
        fieldnames = [
            'Ticket id',
            'Subject line',
            'Date ticket created',
            'Tags',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        while next_page:
            print(next_page)
            response = requests.get(
                next_page,
                headers={'Content-type': 'application/json'},
                auth=(
                    '{}/token'.format(NOTIFY_ZENDESK_EMAIL),
                    ZENDESK_API_KEY
                )
            )
            data = response.json()
            print(data)
            for row in data["results"]:
                service_url = [x for x in row["description"].split('\n')
                               if x.startswith("https://www.notifications.service.gov.uk/services/")]
                service_url = service_url[0][50:] if len(service_url) > 0 else None
                if not service_url:
                    writer.writerow({'Ticket id': row['id'],
                                     'Subject line': row['subject'],
                                     'Date ticket created': row["created_at"],
                                     'Tags': row.get('tags', '')
                                     })
            next_page = data["next_page"]


def get_tickets_with_description():
    ZENDESK_TICKET_URL = 'https://govuk.zendesk.com/api/v2/search.json?query={}'
    query_params = 'type:ticket group:{}, created>2019-07-01'.format(NOTIFY_GROUP_ID)
    query_params = urllib.parse.quote(query_params)

    next_page = ZENDESK_TICKET_URL.format(query_params)
    with open("zendesk_ticket.csv", 'w') as csvfile:
        fieldnames = [
            'Ticket id',
            'Subject line',
            'Description',
            'Date ticket created',
            'Tags',
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        while next_page:
            print(next_page)
            response = requests.get(
                next_page,
                headers={'Content-type': 'application/json'},
                auth=(
                    '{}/token'.format(NOTIFY_ZENDESK_EMAIL),
                    ZENDESK_API_KEY
                )
            )
            data = response.json()
            print(data)
            for row in data["results"]:
                writer.writerow({'Ticket id': row['id'],
                                 'Subject line': row['subject'],
                                 'Description': row['description'],
                                 'Date ticket created': row["created_at"],
                                 'Tags': row.get('tags', '')
                                 })
            next_page = data["next_page"]
