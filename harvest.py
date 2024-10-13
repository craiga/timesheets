"""Harvest."""

from collections.abc import Iterator
from typing import Any, TypedDict

import requests


class PaginatedProjectAssignmentsResponse(TypedDict):
    """Type for a paginated response."""

    links: dict[str, str]
    project_assignments: list[dict[str, Any]]


class Harvest(requests.Session):
    """Harvest client."""

    def __init__(
        self, personal_access_token: str, account_id: str, *args: Any, **kwargs: Any
    ) -> None:
        """Harvest client."""
        super().__init__(*args, **kwargs)
        self.headers["Authorization"] = f"Bearer {personal_access_token}"
        self.headers["Harvest-Account-ID"] = account_id

    def get_logged_in_user(self) -> dict[str, Any]:
        """Get the logged in user."""
        response = self.get("https://api.harvestapp.com/v2/users/me")
        response.raise_for_status()
        return response.json()

    def get_logged_in_user_project_assignments(
        self, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        """Get projects assigned to the logged in user."""
        response_data: PaginatedProjectAssignmentsResponse = {
            "links": {
                "next": "https://api.harvestapp.com/v2/users/me/project_assignments"
            },
            "project_assignments": [],
        }

        while response_data["links"]["next"]:
            response = self.get(response_data["links"]["next"])
            response.raise_for_status()
            response_data = response.json()
            yield from response_data["project_assignments"]

    def create_time_entry(self, time_entry: dict[str, Any]) -> None:
        """Create timeslip."""
        response = self.post(
            "https://api.harvestapp.com/v2/time_entries", json=time_entry
        )
        response.raise_for_status()
