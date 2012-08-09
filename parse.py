#!/usr/bin/env python

import gflags
import httplib2

from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run

from bs4 import BeautifulSoup

import datetime
import sys

firstday = datetime.datetime(2012, 8, 16)
lastday  = datetime.datetime(2012, 11, 30)

oauth_client_id='YOUR INFO HERE'
oauth_client_secret='YOUR INFO HERE'
oauth_user_agent='YOUR INFO HERE'
google_api_key='YOUR INFO HERE'

def day2int(day):
    if day == "M":
        return 0
    elif day == "T":
        return 1
    elif day == "W":
        return 2
    elif day == "Th":
        return 3
    elif day == "F":
        return 4
    else:
        return -1

def int2day(i):
    if i == 0:
        return "MO"
    elif i == 1:
        return "TU"
    elif i == 2:
        return "WE"
    elif i == 3:
        return "TH"
    elif i == 4:
        return "FR"
    elif i == 5:
        return "SA"
    elif i == 6:
        return "SU"
    else:
        return -1

def parse_html(filename):
    soup = BeautifulSoup(open(filename))

    classes = []

    for data in soup.find_all("tbody")[1].contents:
        td = data.find_all("td")
        if not td:
            continue

        cls = {}
        cls["name"]         = td[0].a.contents[0].strip()
        cls["section"]      = td[1].contents[0].strip()
        cls["description"]  = td[2].contents[0].strip()
        cls["credits"]      = td[3].contents[0].strip()
        cls["days"]         = [day2int(day) for day in td[4].contents[0].strip().split()]
        time = [datetime.datetime.strptime(i.strip(), "%I:%M %p") for i in td[5].contents[0].split("-")]
        cls["time"]         = [datetime.timedelta(hours=t.hour, minutes=t.minute) for t in time]
        cls["room"]         = td[6].contents[0].strip()

        classes.append(cls)

    return classes

def google_service():
    FLAGS = gflags.FLAGS

    # Set up a Flow object to be used if we need to authenticate. This
    # sample uses OAuth 2.0, and we set up the OAuth2WebServerFlow with
    # the information it needs to authenticate. Note that it is called
    # the Web Server Flow, but it can also handle the flow for native
    # applications
    # The client_id and client_secret are copied from the API Access tab on
    # the Google APIs Console
    FLOW = OAuth2WebServerFlow(
        client_id=oauth_client_id,
        client_secret=oauth_client_secret,
        scope='https://www.googleapis.com/auth/calendar',
        user_agent=oauth_user_agent)

    # To disable the local server feature, uncomment the following line:
    # FLAGS.auth_local_webserver = False

    # If the Credentials don't exist or are invalid, run through the native client
    # flow. The Storage object will ensure that if successful the good
    # Credentials will get written back to a file.
    storage = Storage('calendar.dat')
    credentials = storage.get()
    if credentials is None or credentials.invalid == True:
      credentials = run(FLOW, storage)

    # Create an httplib2.Http object to handle our HTTP requests and authorize it
    # with our good Credentials.
    http = httplib2.Http()
    http = credentials.authorize(http)

    # Build a service object for interacting with the API. Visit
    # the Google APIs Console
    # to get a developerKey for your own application.
    return build(serviceName='calendar', version='v3', http=http, developerKey=google_api_key)

def start_date(days):
    day = datetime.timedelta(days=1)
    retday = firstday

    while retday.weekday() not in days:
        retday += day

    return retday

def end_date(days):
    day = datetime.timedelta(days=1)
    retday = lastday

    while retday.weekday() not in days:
        retday -= day

    return retday

def dateTime(day, time, delimiters=True):
    if delimiters:
        date = day + time
        return date.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        # Hackalious!
        date = day + time + datetime.timedelta(hours=12)
        return date.strftime("%Y%m%dT%H%M%SZ")

def days2str(days):
    string = ""

    for i, day in enumerate(days):
        if i != 0:
            string += ","

        string += int2day(day)

    return string

def select_calendar(service):
    calendar_list = service.calendarList().list().execute()

    for i, cal in enumerate(calendar_list["items"]):
        print "%s: %s" % (i, cal["summary"])

    selection = int(raw_input("Select a calendar # to add to: "))

    if selection < 0 or selection >= len(calendar_list["items"]):
        print "You have failed at selecting a calendar.  I am not sorry"
        print "If you desired calendar did not appear, I am sorry"
        exit(1)

    return calendar_list["items"][selection]["id"]

def build_event(cls):
    event = {}

    event["summary"] = cls["name"] + " Section " + cls["section"]
    event["description"] = cls["name"] + ": " + cls["description"] + "\n" + cls["credits"] + " credits"
    event["location"] = cls["room"]

    event["start"] = {
            "dateTime": dateTime(start_date(cls["days"]), cls["time"][0]),
            "timeZone": "America/New_York"}
    event["end"]   = {
            "dateTime": dateTime(start_date(cls["days"]), cls["time"][1]),
            "timeZone": "America/New_York"}
    event["recurrence"] = ["RRULE:FREQ=WEEKLY;UNTIL=%s;BYDAY=%s" % (dateTime(end_date(cls["days"]), cls["time"][1], delimiters=False), days2str(cls["days"]))]

    return event

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "Usage: %s FILE" % sys.argv[0]
        print "FILE is the HTML file from NCSU Course Timetable, accessible by"
        print "clicking 'Schedule Grid View' from 'My Class Schedule' in MyPack Portal."
        exit(1)

    print "First day of class set to %s" % firstday.strftime("%Y-%b-%d")
    print "Last day of class set to %s\n" % lastday.strftime("%Y-%b-%d")

    classes = parse_html(sys.argv[1])

    for cls in classes:
        print "%s Section %s: %s,\tMeets %s from %s to %s" % (cls["name"], cls["section"], cls["description"], days2str(cls["days"]), str(cls["time"][0]), str(cls["time"][1]))

    if raw_input("Are these classes correct? (y/n) ") != "y":
        print "I have failed you, and I am sorry."
        exit(1)

    service = google_service()

    calendar_id = select_calendar(service)

    i = 1
    for cls in classes:
        created_event = service.events().insert(calendarId=calendar_id, body=build_event(cls)).execute()

        if created_event:
            print "Successfully added class %d" % i
        else:
            print "Failed to add class %d" % i

        i += 1
