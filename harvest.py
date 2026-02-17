"""Harvest."""

from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from collections.abc import Iterator


class Harvest(requests.Session):
    """Harvest client."""

    def __init__(
        self, personal_access_token: str, account_id: str, *args: Any, **kwargs: Any
    ) -> None:
        """Harvest client."""
        super().__init__(*args, **kwargs)
        self.headers["Authorization"] = f"Bearer {personal_access_token}"
        self.headers["Harvest-Account-Id"] = account_id

    def get_logged_in_user(self) -> dict[str, Any]:
        """Get the logged in user."""
        response = self.get("https://api.harvestapp.com/v2/users/me")
        response.raise_for_status()
        user: dict[str, Any] = response.json()
        return user

    def get_logged_in_user_project_assignments(
        self, **kwargs: Any
    ) -> Iterator[dict[str, Any]]:
        """Get projects assigned to the logged in user."""
        response_data: dict[str, Any] = {
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

    def create_time_entry(self, time_entry: dict[str, Any]) -> dict[str, Any]:
        """Create time entry."""
        response = self.post(
            "https://api.harvestapp.com/v2/time_entries", json=time_entry
        )
        response.raise_for_status()
        response_time_entry: dict[str, Any] = response.json()
        return response_time_entry

    def get_time_entry(self, time_entry_id: int) -> dict[str, Any]:
        """Create time entry."""
        response = self.get(
            f"https://api.harvestapp.com/v2/time_entries/{time_entry_id}"
        )
        response.raise_for_status()
        response_time_entry: dict[str, Any] = response.json()
        return response_time_entry

    def update_time_entry(
        self, time_entry_id: int, time_entry: dict[str, Any]
    ) -> dict[str, Any]:
        """Update time entry."""
        response = self.patch(
            f"https://api.harvestapp.com/v2/time_entries/{time_entry_id}",
            json=time_entry,
        )
        response.raise_for_status()
        response_time_entry: dict[str, Any] = response.json()
        return response_time_entry
