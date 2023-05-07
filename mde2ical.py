#!/usr/bin/env python3

import json
import icalendar
import pytz
import sys
import os
import hashlib
import uuid
from dateutil import parser
import dateutil.parser
from datetime import datetime
from datetime import timedelta
import jsonpath_ng.ext

## Instantiate
cal = icalendar.Calendar()
cal.add('prodid', '-//MDE2iCal//jfautley//')
cal.add('version', '2.0')
cal.add('X-WR-RELCALID', 'mde2ical//disney')

# Update timezone
PARK_TIMEZONE = "America/New_York"

# How long to eat?
FEEDING_TIME = timedelta(hours=1, minutes=30)

try:
    with open(sys.argv[1], 'r') as f:
        plans = json.load(f)
except:
    print(f"Usage: {sys.argv[0]} <filename>")
    sys.exit(1)

def gen_uid(id):
    return str(uuid.UUID(bytes=hashlib.md5(id.encode()).digest()))

def process_resort_checkin(event, lastDayOfStay):
    ci = parser.parse(event['startDate']).date()
    # Whole day events end at midnight, so we "lose" a day at the end of our
    # reservation. We check the plans before arriving here and treat a check-in
    # and check-out event on the same day as a coninuous trip. If we are
    # 'lastDayOfStay' then we append +1 day to the checkout date to complete
    # the calendar entry.
    # RFC5545 confirms DTEND is "non-inclusive", for reference.
    co = parser.parse(event['endDate']).date()
    #if lastDayOfStay:
    #    co = co + timedelta(days = 1)
    e = icalendar.Event()
    e.add('uid', gen_uid(event['id']))
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
    e.add('uid', gen_uid(event['id']))
    e.add('dtstart', event_time)
    e.add('dtend', event_time + FEEDING_TIME)
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
    e.add('uid', gen_uid(event['id']))
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
    e.add('uid', gen_uid(event['id']))
    e.add('dtstart', event_time)
    e.add('dtend', event_time + timedelta(hours=2))
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

# Obtain Ticketing Information
for ticket in plans['parkAdmissions']['tickets']['admissions']:
    # Process Park Tickets (used only for SPECIAL_EVENT tickets for now)
    if ticket.get('type') == 'PARK_ADMISSION' and ticket.get('subType') == 'SPECIAL_EVENT':
        try:
            event_time = parser.parse(ticket['title'], fuzzy=True)
        except dateutil.parser.ParserError:
            print(f"ERROR: Unable to determine event time of {ticket['title']} -- SKIPPING")
            continue

        # Crude de-dup by looking for the reassignable portion of the ticket (i.e. the 'main holder')
        if not ticket.get('reassignableTo'):
            continue

        # Get the park hours for the special event
        jp = jsonpath_ng.ext.parse(f'$.days[?(@.date=="{event_time.date()}")].plans[?(@.type=="PARK_HOURS")]')
        for m in jp.find(plans):
            park_name = m.value['title']
            if park_name in ticket['title']:
                e = icalendar.Event()
                e.add('uid', gen_uid(ticket['id']))
                e.add('dtstart', parser.parse(f"{event_time} {m.value['specialEventStartAt']}"))
                e.add('dtend', parser.parse(f"{event_time} {m.value['specialEventEndAt']}") + timedelta(days=1))
                e.add('summary', ticket['title'])
                cal.add_component(e)

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

outfile = f"{os.path.splitext(sys.argv[1])[0]}.ics"
out = open(outfile, 'wb')
out.write(cal.to_ical())
out.close()

print(f"Calendar has been output to {outfile}")
