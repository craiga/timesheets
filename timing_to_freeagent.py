#!/usr/bin/env python
"""Copy timesheet entries from Timing to FreeAgent."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

from freeagent import FreeAgent, FreeAgentAuthCodeListener
from timing import Timing

TIMEZONE = datetime.now(UTC).astimezone().tzinfo


class TimingProjectToFreeAgentMap(dict[str, dict[str, str]]):
    """Timing project to FreeAgent map."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Timing project to FreeAgent map."""  # noqa: D401
        self._path = Path(".timing-project-to-freeagent-map")
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
@click.option("--freeagent-oauth-id")
@click.option("--freeagent-oauth-secret")
@click.option("--ngrok-domain")
@click.option(
    "--date-from",
    type=click.DateTime(),
    default=datetime.now(tz=TIMEZONE) - timedelta(days=7),
)
@click.option("--date-until", type=click.DateTime(), default=datetime.now(tz=TIMEZONE))
def main(  # noqa: PLR0913
    timing_personal_access_token: str,
    freeagent_oauth_id: str,
    freeagent_oauth_secret: str,
    ngrok_domain: str | None,
    date_from: datetime,
    date_until: datetime | None,
) -> None:
    """Copy timesheet entries from Timing to FreeAgent."""
    timing_to_freeagent_map = TimingProjectToFreeAgentMap()
    timing_to_freeagent_map.load()

    with (
        Timing(timing_personal_access_token) as timing,
        FreeAgent(freeagent_oauth_id) as freeagent,
    ):
        if not freeagent.authorized:
            listener = FreeAgentAuthCodeListener(ngrok_domain)
            click.echo(
                f"Please make sure {listener.ngrok.url()} is registered as an OAuth"
                " redirect URI for this app at https://dev.freeagent.com/apps."
            )
            click.echo(f"Visit {freeagent.get_authorization_url(listener)}")
            freeagent.fetch_token(
                "https://api.freeagent.com/v2/token_endpoint",
                code=listener.wait_for_auth_code(),
                client_id=freeagent_oauth_id,
                client_secret=freeagent_oauth_secret,
            )

        freeagent_user = freeagent.get_logged_in_user()

        for time_entry in timing.get_time_entries(
            load_projects=True, start_date_min=date_from, start_date_max=date_until
        ):
            project_id = time_entry["project"]["self"].removeprefix("/projects/")

            if project_id not in timing_to_freeagent_map:
                tasks = list(freeagent.get_tasks(load_projects=True, view="active"))
                for task_index, task in enumerate(tasks):
                    click.echo(
                        f"{task_index}: {task["project"]["name"]} — {task["name"]}"
                    )

                selected_task = tasks[
                    int(
                        click.prompt(
                            (
                                "Map Timing project "
                                + " ".join(time_entry["project"]["title_chain"])
                                + " to which FreeAgent task?"
                            ),
                            type=click.Choice([str(i) for i in range(len(tasks))]),
                            show_choices=False,
                        )
                    )
                ]
                timing_to_freeagent_map[project_id] = {
                    "task": selected_task["url"],
                    "project": selected_task["project"]["url"],
                }
                timing_to_freeagent_map.save()

            freeagent_project_data = timing_to_freeagent_map[project_id]
            freeagent.create_timeslip({
                "task": freeagent_project_data["task"],
                "project": freeagent_project_data["project"],
                "user": freeagent_user["url"],
                "dated_on": str(time_entry["start_date"].date()),
                # Hours rounded to nearest five minutes.
                "hours": round(
                    (time_entry["end_date"] - time_entry["start_date"]).total_seconds()
                    / 300
                )
                / 12,
            })


if __name__ == "__main__":
    load_dotenv()
    main(auto_envvar_prefix="TIMING_TO_FREEAGENT")
