#!/usr/bin/env python3

import json
import icalendar
import pytz
import sys
import os
from dateutil import parser
from datetime import datetime

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

def process_resort_checkin(event):
    ci = parser.parse(f"{event['startDate']} {event['checkInTime']}").replace(tzinfo=pytz.timezone(PARK_TIMEZONE))
    co = parser.parse(f"{event['endDate']} {event['checkOutTime']}").replace(tzinfo=pytz.timezone(PARK_TIMEZONE))
    e = icalendar.Event()
    e.add('dtstart', ci)
    e.add('dtend', co)
    e.add('summary', f"Staying at {event['title']}")
    e.add('url', event['links']['finder']['href'])
    
    if len(event['guests']) > 0:
        print("Guests:")
        for g in event['guests']:
            e.add('attendee', guests[g['id']])
            print(f"\t{guests[g['id']]}")
    return(e)

def process_dining(event):
    event_time = parser.parse(f"{event['startDate']} {event['startTime']}").replace(tzinfo=pytz.timezone(PARK_TIMEZONE))
    e = icalendar.Event()
    e.add('dtstart', event_time)
    e.add('summary', event['title'])

    event_url = event['links'].get('finder')
    if event_url:
        e.add('url', event_url['href'])

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
        if event['type'] == 'RESORT':
            if event['subType'] != 'RESORT_ROOM_CHECKIN':
                continue
            cal.add_component(process_resort_checkin(event))


        if event['type'] == 'DINING':
            cal.add_component(process_dining(event))
        #print(f"Event: {event['type']} / {event['title']}")

outfile = f"{os.path.splitext(sys.argv[1])[0]}.vcs"
out = open(outfile, 'wb')
out.write(cal.to_ical())
out.close()

print(f"Calendar has been output to {outfile}")
