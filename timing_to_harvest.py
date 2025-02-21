#!/usr/bin/env python
"""Copy timesheet entries from Timing to Harvest."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

from datetime_helpers import TIMEZONE, round_to_nearest_five_minutes
from harvest import Harvest
from timing import Timing


class TimingProjectToHarvestMap(dict[str, dict[str, str]]):
    """Timing project to Harvest map."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Timing project to Harvest map."""  # noqa: D401
        self._path = Path(".timing-project-to-harvest-map")
        super().__init__(*args, **kwargs)

    def load(self) -> None:
        """Load data."""
        if not self._path.exists():
            with self._path.open(mode="w") as fp:
                json.dump({}, fp)

        with self._path.open(mode="r") as fp:
            loaded_data = json.load(fp)
            self.update(loaded_data)

    def save(self) -> None:
        """Save data."""
        with self._path.open(mode="w") as fp:
            json.dump(self, fp)


@click.command()
@click.option(
    "--timing-personal-access-token",
    help=(
        "Personal access token for accessing Timing. Visit"
        " https://web.timingapp.com/integrations/tokens to get a token."
    ),
)
@click.option(
    "--harvest-personal-access-token",
    help=(
        "Personal access token for accessing Harvest. Visit"
        " https://id.getharvest.com/developers to get a token."
    ),
)
@click.option("--harvest-account-id")
@click.option(
    "--date-from",
    type=click.DateTime(),
    default=datetime.now(tz=TIMEZONE) - timedelta(days=7),
)
@click.option("--date-until", type=click.DateTime(), default=datetime.now(tz=TIMEZONE))
def main(
    timing_personal_access_token: str,
    harvest_personal_access_token: str,
    harvest_account_id: str,
    date_from: datetime,
    date_until: datetime | None,
) -> None:
    """Copy timesheet entries from Timing to Harvest."""
    timing_to_harvest_map = TimingProjectToHarvestMap()
    timing_to_harvest_map.load()

    with (
        Timing(timing_personal_access_token) as timing,
        Harvest(harvest_personal_access_token, harvest_account_id) as harvest,
    ):
        for time_entry in timing.get_time_entries(
            load_projects=True, start_date_min=date_from, start_date_max=date_until
        ):
            project_id = time_entry["project"]["self"].removeprefix("/projects/")

            if project_id not in timing_to_harvest_map:
                project_assignments = list(
                    harvest.get_logged_in_user_project_assignments()
                )
                projects = [assignment["project"] for assignment in project_assignments]
                project_name = click.prompt(
                    (
                        "Map Timing project "
                        + " ".join(time_entry["project"]["title_chain"])
                        + " "
                        + time_entry["title"]
                        + " to which Harvest project?"
                    ),
                    type=click.Choice([project["name"] for project in projects]),
                    show_choices=True,
                )

                project_assignment = {
                    assignment["project"]["name"]: assignment
                    for assignment in project_assignments
                }[project_name]

                tasks = [
                    assignment["task"]
                    for assignment in project_assignment["task_assignments"]
                ]
                task_name = click.prompt(
                    (
                        "Map Timing task "
                        + " ".join(time_entry["project"]["title_chain"])
                        + " "
                        + time_entry["title"]
                        + " to which Harvest task?"
                    ),
                    type=click.Choice([task["name"] for task in tasks]),
                    show_choices=True,
                )

                timing_to_harvest_map[project_id] = {
                    "task_id": {task["name"]: task["id"] for task in tasks}[task_name],
                    "project_id": project_assignment["project"]["id"],
                }
                timing_to_harvest_map.save()

            harvest_project_data = timing_to_harvest_map[project_id]

            harvest.create_time_entry({
                "task_id": harvest_project_data["task_id"],
                "project_id": harvest_project_data["project_id"],
                "spent_date": str(time_entry["start_date"].date()),
                "started_time": (
                    round_to_nearest_five_minutes(time_entry["start_date"])
                    .time()
                    .strftime("%I:%M%p")
                ),
                "ended_time": (
                    round_to_nearest_five_minutes(time_entry["end_date"])
                    .time()
                    .strftime("%I:%M%p")
                ),
            })


if __name__ == "__main__":
    load_dotenv()
    main(auto_envvar_prefix="TIMING_TO_HARVEST")
