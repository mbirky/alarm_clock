from __future__ import print_function
import datetime
import pickle
import os.path
import subprocess
import argparse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def main(service, calendar_id, quiet):
    """
    Start the process of reading the next calendar entry from a google clander
    and then starting rhythmbox whenever an event starts.
    """
    next_update_time = datetime.datetime.now()
    next_alarm = None
    previous_alarm = None

    while True:
        now = datetime.datetime.now()

        # Check if alarm should go off
        if next_alarm and now >= next_alarm:
            print(f"Alarm at: {datetime.datetime.now()}")
            if not quiet:
                subprocess.Popen(["/usr/bin/rhythmbox-client", "--play"])
            previous_alarm = next_alarm
            next_alarm = None

        # Update the next alarm time
        if now > next_update_time:
            print(f"Update at: {now}")
            next_alarm = get_next_event(service, calendar_id)
            if next_alarm == previous_alarm:
                next_alarm = None
            next_update_time = now + datetime.timedelta(minutes=5)

def create_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)

def get_next_event(service, calendar_id):
    """
    Gets the next event in the google calendar and then returns either a
    datetime of the start date, or None if no mare events.
    """
    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    alarm_calendar_id = calendar_id

    events_result = (
        service.events()
        .list(
            calendarId=alarm_calendar_id,
            timeMin=now,
            maxResults=1,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if events:
        event_time = events[0]["start"].get("dateTime", events[0]["start"].get("date"))
        return datetime.datetime.strptime(event_time[:-6], "%Y-%m-%dT%H:%M:%S")
    return None

def get_calanders(service):
    calendars_result = (
        service.calendarList()
        .list()
        .execute()
    )
    return calendars_result.get("items", [])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="An alarm clock set by Google Calander")
    parser.add_argument('-q', '--quiet', action="store_true",
                        help="Music will not play when an alarm goes off")
    parser.add_argument('-l', '--list', action="store_true",
                        help="list avalible calanders")
    
    args = parser.parse_args()

    service = create_service()

    if args.list:
        print("Calendar Summary: Calendar ID")
        for calendar in get_calanders(service):
            print(f"{calendar['summary']}: {calendar['id']}")
        exit()

    calendar_id = ""
    with open(".calendar_id", "r") as file:
        calendar_id = file.readline()

    main(service, calendar_id, args.quiet)
