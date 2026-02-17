"""Timing."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict
from urllib.parse import urlencode

import requests

if TYPE_CHECKING:
    from collections.abc import Iterator


class PaginatedResponse(TypedDict):
    """Type for a paginated response."""

    links: dict[str, str]
    data: list[dict[str, Any]]


class Timing(requests.Session):
    """Timing client."""

    def __init__(self, personal_access_token: str, *args: Any, **kwargs: Any) -> None:
        """Timing client."""  # noqa: D401
        super().__init__(*args, **kwargs)
        self.headers["Authorization"] = f"Bearer {personal_access_token}"

    def get_time_entries(
        self,
        *,
        load_projects: bool = False,
        start_date_min: datetime | None = None,
        start_date_max: datetime | None = None,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        """Get time entries."""
        query_data = kwargs
        if start_date_min:
            query_data["start_date_min"] = str(start_date_min.date())
        if start_date_max:
            query_data["start_date_max"] = str(start_date_max.date())

        response_data: PaginatedResponse = {
            "links": {
                "next": "https://web.timingapp.com/api/v1/time-entries?"
                + urlencode(query_data, doseq=True)
            },
            "data": [],
        }

        while response_data["links"]["next"]:
            response = self.get(response_data["links"]["next"])
            response.raise_for_status()
            response_data = response.json()
            for time_entry in response_data["data"]:
                time_entry["start_date"] = datetime.fromisoformat(
                    time_entry["start_date"]
                )
                time_entry["end_date"] = datetime.fromisoformat(time_entry["end_date"])
                if load_projects:
                    time_entry["project"] = self.get_project(
                        time_entry["project"]["self"], load_projects=load_projects
                    )

                yield time_entry

    def get_project_hierarchy(self) -> dict[str, Any]:
        """Get project hierarchy."""
        response = self.get("https://web.timingapp.com/api/v1/projects/hierarchy")
        response.raise_for_status()
        project_hierarchy: dict[str, Any] = response.json()["data"]
        return project_hierarchy

    def get_project(
        self, project_id: str, *, load_projects: bool = False
    ) -> dict[str, Any]:
        """Get project details."""
        project_id = project_id.removeprefix("/projects/")
        response = self.get(f"https://web.timingapp.com/api/v1/projects/{project_id}")
        response.raise_for_status()
        project: dict[str, dict[str, Any]] = response.json()["data"]

        if project["parent"] and load_projects:
            project["parent"] = self.get_project(
                project["parent"]["self"], load_projects=load_projects
            )

        return project

    def set_custom_field_in_project(
        self, project_id: str, key: str, value: Any
    ) -> None:
        """Set a custom field in project."""
        if value is not None:
            value = str(value)

        project_id = project_id.removeprefix("/projects/")
        response = self.patch(
            f"https://web.timingapp.com/api/v1/projects/{project_id}",
            json={"custom_fields": {key: value}},
        )
        response.raise_for_status()

    def set_custom_field_in_time_entry(
        self, time_entry_id: str, key: str, value: Any
    ) -> None:
        """Set a custom field in project."""
        if value is not None:
            value = str(value)

        time_entry_id = time_entry_id.removeprefix("/time-entries/")
        response = self.patch(
            f"https://web.timingapp.com/api/v1/time-entries/{time_entry_id}",
            json={"custom_fields": {key: value}},
        )
        response.raise_for_status()
