#!/usr/bin/env python3

import json
import icalendar
import pytz
import sys
import os
from dateutil import parser
from datetime import datetime
from datetime import timedelta

## Instantiate
cal = icalendar.Calendar()

# Update timezone
PARK_TIMEZONE = "America/New_York"

try:
    with open(sys.argv[1], 'r') as f:
        plans = json.load(f)
except:
    print(f"Usage: {sys.argv[0]} <filename>")
    sys.exit(1)

def process_resort_checkin(event, lastDayOfStay):
    ci = parser.parse(event['startDate']).date()
    # Whole day events end at midnight, so we "lose" a day at the end of our
    # reservation. We check the plans before arriving here and treat a check-in
    # and check-out event on the same day as a coninuous trip. If we are
    # 'lastDayOfStay' then we append +1 day to the checkout date to complete
    # the calendar entry.
    # RFC5545 confirms DTEND is "non-inclusive", for reference.
    co = parser.parse(event['endDate']).date()
    if lastDayOfStay:
        co = co + timedelta(days = 1)
    e = icalendar.Event()
    e.add('uid', event['id'])
    e.add('dtstart', ci)
    e.add('dtend', co)
    e.add('summary', f"Staying at {event['title']}")

    descriptionString = f"Confirmation Number: {event['confirmationNumber']}\nRoom Type: {event['roomType']}"
    e.add('description', descriptionString)

    event_url = event['links'].get('finder')
    if event_url:
        e.add('url', event_url['href'])
    
    if len(event['guests']) > 0:
        for g in event['guests']:
            e.add('attendee', guests[g['id']])
    return(e)

def process_dining(event):
    event_time = parser.parse(f"{event['startDate']} {event['startTime']}").replace(tzinfo=pytz.timezone(PARK_TIMEZONE))
    e = icalendar.Event()
    e.add('uid', event['id'])
    e.add('dtstart', event_time)
    e.add('summary', event['title'])
    e.add('location', event['location'])

    descriptionString = f"Confirmation Number: {event['confirmationNumber']}\nContact Number: tel:+1-{event['facilityPhoneNumber'].replace(' ', '-')}"
    e.add('description', descriptionString)

    event_url = event['links'].get('finder')
    if event_url:
        e.add('url', event_url['href'])

    if len(event['guests']) > 0:
        for g in event['guests']:
            e.add('attendee', guests[g['guest']['id']])

    return(e)

def process_park_reservation(event):
    # Don't add a time to a park reservation as we don't want to block our calendar for the whole day.
    event_date = parser.parse(event['startDate']).date()
    e = icalendar.Event()

    # The ID for a park pass seems to change, so lets set something 'well
    # known', as this also allows the calendar to update when people swap their
    # plans around.
    e.add('uid', f"parkpass-{event['startDate']}")
    e.add('dtstart', event_date)
    e.add('summary', event['location'])

    event_url = event['links'].get('finder')
    if event_url:
        e.add('url', event_url['href'])

    if len(event['guests']) > 0:
        for g in event['guests']:
            e.add('attendee', guests[g['id']])

    return(e)

def process_activity(event):
    event_time = parser.parse(f"{event['startDate']} {event['startTime']}").replace(tzinfo=pytz.timezone(PARK_TIMEZONE))
    e = icalendar.Event()
    e.add('uid', event['id'])
    e.add('dtstart', event_time)
    e.add('summary', event['title'])

    event_url = event['links'].get('finder')
    if event_url:
        e.add('url', event_url['href'])

    if len(event['guests']) > 0:
        for g in event['guests']:
            e.add('attendee', guests[g['id']])

    return(e)

# Load and store guest information
guests = {}
for guest in plans['guests']:
    guests[guest['id']] = f"{guest['name']['first']} {guest['name']['last']}"

# Iterate over the plans and generate iCalendar events
for day in plans['days']:
    print(f"Processing day: {day['date']}, contains {len(day['plans'])} events.")
    for event in day['plans']:
        # Ignore park open/close events
        if event['type'] == 'PARK_HOURS':
            continue

        # Process resort checkin - this include our CI/CO dates, so we can
        # ignore the RESORT_ROOM_CHECKOUT object, as well as the per-day
        # RESORT_STAY objects.
        # We also do some testing here to see if this is a
        # split-ticket/continuous 'trip' - this feeds into the calendar event
        # generation for the resort stay(s) to ensure we don't drop our last
        # day.
        if event['type'] == 'RESORT' and event['subType'] == 'RESORT_ROOM_CHECKIN':
            lastDayOfStay = True

            # Iterate over our days to find our check-out day, and see if this the last day of our stay.
            for d in plans['days']:
                if event['endDate'] == d['date']:
                    # This is our check-out date - check our reservations for this day.
                    for e in d['plans']:
                        if e['type'] == 'RESORT' and e['subType'] == 'RESORT_ROOM_CHECKIN':
                            # We have both check-in and check-out events ont he same day, this is a continuing trip.
                            lastDayOfStay = False

            cal.add_component(process_resort_checkin(event, lastDayOfStay))

        # Process dining events
        if event['type'] == 'DINING':
            cal.add_component(process_dining(event))

        # Process 'activities' (i.e. tours, special events)
        if event['type'] == 'ACTIVITY':
            cal.add_component(process_activity(event))

        # Process Park Reservations
        if event.get('type') == "PARK_RESERVATION":
            cal.add_component(process_park_reservation(event))

outfile = f"{os.path.splitext(sys.argv[1])[0]}.vcs"
out = open(outfile, 'wb')
out.write(cal.to_ical())
out.close()

print(f"Calendar has been output to {outfile}")
