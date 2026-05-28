"""
ARIA - Google Calendar Service
Full Calendar API integration: list, create, update, delete events.
"""
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from services.google.auth import get_google_credentials
from core.logger import get_logger

logger = get_logger("calendar_service")


class CalendarService:
    """Manages Google Calendar operations via the Calendar API."""

    def __init__(self, config=None):
        self.config = config
        self._service = None

    def _get_service(self):
        """Lazy-load the Calendar API service."""
        if self._service is None:
            creds = get_google_credentials(self.config)
            if creds is None:
                raise Exception(
                    "No Google credentials available. "
                    "Run the auth flow first."
                )
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def is_ready(self) -> bool:
        try:
            self._get_service()
            return True
        except Exception:
            return False

    def list_events(
        self, max_results: int = 10, days_ahead: int = 7
    ) -> list[dict]:
        """
        List upcoming events from the primary calendar.
        days_ahead: how many days into the future to look.
        """
        try:
            service = self._get_service()
            now = datetime.utcnow()
            time_min = now.isoformat() + "Z"
            time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            result = []
            for event in events:
                start = event["start"].get(
                    "dateTime", event["start"].get("date", "")
                )
                end = event["end"].get(
                    "dateTime", event["end"].get("date", "")
                )
                result.append({
                    "id": event.get("id", ""),
                    "summary": event.get("summary", "(Sin titulo)"),
                    "start": start,
                    "end": end,
                    "location": event.get("location", ""),
                    "description": event.get("description", ""),
                    "status": event.get("status", ""),
                })

            return result

        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return [{"error": str(e)}]

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        timezone: str = "America/New_York",
    ) -> dict:
        """
        Create a new calendar event.
        start_time / end_time: ISO 8601 format, e.g. '2026-05-27T10:00:00'
        """
        try:
            service = self._get_service()
            event_body = {
                "summary": summary,
                "location": location,
                "description": description,
                "start": {
                    "dateTime": start_time,
                    "timeZone": timezone,
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": timezone,
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "popup", "minutes": 15},
                    ],
                },
            }

            created = (
                service.events()
                .insert(calendarId="primary", body=event_body)
                .execute()
            )

            logger.info(f"Event created: {created.get('htmlLink')}")
            return {
                "success": True,
                "event_id": created.get("id"),
                "link": created.get("htmlLink"),
                "summary": summary,
                "start": start_time,
                "end": end_time,
            }

        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {"success": False, "error": str(e)}

    def update_event(
        self,
        event_id: str,
        summary: str = "",
        start_time: str = "",
        end_time: str = "",
        description: str = "",
        location: str = "",
        timezone: str = "America/New_York",
    ) -> dict:
        """Update an existing calendar event."""
        try:
            service = self._get_service()

            # Get current event
            event = (
                service.events()
                .get(calendarId="primary", eventId=event_id)
                .execute()
            )

            # Update only provided fields
            if summary:
                event["summary"] = summary
            if description:
                event["description"] = description
            if location:
                event["location"] = location
            if start_time:
                event["start"] = {
                    "dateTime": start_time,
                    "timeZone": timezone,
                }
            if end_time:
                event["end"] = {
                    "dateTime": end_time,
                    "timeZone": timezone,
                }

            updated = (
                service.events()
                .update(
                    calendarId="primary",
                    eventId=event_id,
                    body=event,
                )
                .execute()
            )

            logger.info(f"Event updated: {updated.get('htmlLink')}")
            return {
                "success": True,
                "event_id": updated.get("id"),
                "link": updated.get("htmlLink"),
            }

        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return {"success": False, "error": str(e)}

    def delete_event(self, event_id: str) -> dict:
        """Delete a calendar event by ID."""
        try:
            service = self._get_service()
            service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
            logger.info(f"Event deleted: {event_id}")
            return {"success": True, "deleted_id": event_id}
        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {"success": False, "error": str(e)}

    def find_free_slots(
        self, date: str, duration_minutes: int = 60
    ) -> list[dict]:
        """
        Find free time slots on a given date.
        date: 'YYYY-MM-DD' format.
        """
        try:
            service = self._get_service()
            time_min = f"{date}T08:00:00Z"
            time_max = f"{date}T22:00:00Z"

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # Build busy periods
            busy = []
            for event in events:
                start = event["start"].get("dateTime", "")
                end = event["end"].get("dateTime", "")
                if start and end:
                    busy.append((
                        datetime.fromisoformat(start.replace("Z", "+00:00")),
                        datetime.fromisoformat(end.replace("Z", "+00:00")),
                    ))

            # Find free slots between 8 AM and 10 PM
            free_slots = []
            work_start = datetime.fromisoformat(f"{date}T08:00:00+00:00")
            work_end = datetime.fromisoformat(f"{date}T22:00:00+00:00")
            current = work_start
            dur = timedelta(minutes=duration_minutes)

            for b_start, b_end in sorted(busy):
                if current + dur <= b_start:
                    free_slots.append({
                        "start": current.isoformat(),
                        "end": b_start.isoformat(),
                    })
                current = max(current, b_end)

            if current + dur <= work_end:
                free_slots.append({
                    "start": current.isoformat(),
                    "end": work_end.isoformat(),
                })

            return free_slots

        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            return [{"error": str(e)}]
