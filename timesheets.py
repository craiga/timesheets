"""Command-line interface."""

from http import HTTPStatus
from typing import Any

import click
from dotenv import load_dotenv
from requests.exceptions import HTTPError

from datetime_helpers import round_to_nearest_five_minutes
from harvest import Harvest
from timing import Timing


@click.group
def main() -> None:
    """Timesheet tools."""


@main.group
@click.option(
    "--personal-access-token",
    help=(
        "Personal access token for accessing Harvest. Visit"
        " https://id.getharvest.com/developers to get a token."
    ),
    envvar="HARVEST_PERSONAL_ACCESS_TOKEN",
)
@click.option("--account-id", envvar="HARVEST_ACCOUNT_ID")
@click.pass_context
def harvest(ctx: click.Context, personal_access_token: str, account_id: str) -> None:
    """Harvest commands."""
    ctx.obj = Harvest(
        personal_access_token=personal_access_token, account_id=account_id
    )


@harvest.command()
@click.pass_obj
def list_tasks(harvest_api: Harvest) -> None:
    """List clients, projects, and tasks."""
    for proj_assignment in harvest_api.get_logged_in_user_project_assignments():
        click.echo(proj_assignment["client"]["name"])
        click.echo(
            f"\t{proj_assignment['project']['name']}"
            f" (project {proj_assignment['project']['id']})"
        )
        for task_assignment in proj_assignment["task_assignments"]:
            click.echo(
                f"\t\t{task_assignment['task']['name']}"
                f" (task {task_assignment['task']['id']})"
            )


@main.group
@click.option(
    "--personal-access-token",
    help=(
        "Personal access token for accessing Timing. Visit"
        " https://web.timingapp.com/integrations/tokens to get a token."
    ),
    envvar="TIMING_PERSONAL_ACCESS_TOKEN",
)
@click.pass_context
def timing(ctx: click.Context, personal_access_token: str) -> None:
    """Timing commands."""  # noqa: D401
    ctx.obj = Timing(personal_access_token=personal_access_token)


@timing.command()
@click.pass_obj
def list_projects(timing_api: Timing) -> None:
    """List projects hierarchically."""

    def show_project(project: dict[str, Any], prefix: str = "") -> None:
        harvest_project_id = project["custom_fields"].get("harvest_project_id")
        harvest_task_id = project["custom_fields"].get("harvest_task_id")
        suffix = ""
        if harvest_project_id or harvest_task_id:
            suffix_parts = []
            if harvest_project_id:
                suffix_parts.append("project " + harvest_project_id)
            if harvest_task_id:
                suffix_parts.append("task " + harvest_task_id)

            suffix = f" (Harvest {'; '.join(suffix_parts)})"

        click.echo(f"{prefix}{project['title']} ({project['self']}){suffix}")
        for child_project in project["children"]:
            show_project(child_project, prefix + "\t")

    for project in timing_api.get_project_hierarchy():
        show_project(project)


@timing.command()
@click.argument("timing_project_id")
@click.argument("harvest_project_id")
@click.pass_obj
def set_harvest_project_id(
    timing_api: Timing, timing_project_id: str, harvest_project_id: str
) -> None:
    """Set Harvest project ID in Timing project."""
    timing_api.set_custom_field_in_project(
        timing_project_id, "harvest_project_id", harvest_project_id
    )


@timing.command()
@click.argument("timing_project_id")
@click.argument("harvest_task_id")
@click.pass_obj
def set_harvest_task_id(
    timing_api: Timing, timing_project_id: str, harvest_task_id: str
) -> None:
    """Set Harvest task ID in Timing project."""
    timing_api.set_custom_field_in_project(
        timing_project_id, "harvest_task_id", harvest_task_id
    )


class CustomFieldNotFoundInHierarchyError(RuntimeError):
    """Custom field not found in hierarchy error."""


def get_custom_field_from_project_hierarchy(key: str, project: dict[str, Any]) -> Any:
    """Get custom field from project hierarchy."""
    value = None
    while project:
        value = project["custom_fields"].get(key)
        if value is not None:
            break

        project = project["parent"]

    if value is None:
        raise CustomFieldNotFoundInHierarchyError

    return value


class HarvestProjectIDNotSetError(RuntimeError):
    """Harvest project ID not set error."""

    def __init__(self, time_entry: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        """Harvest project ID not set error."""
        super().__init__(
            (
                "Harvest project ID not set for Timing project"
                f" {time_entry['project']['title']}"
            ),
            time_entry,
            *args,
            **kwargs,
        )


class HarvestTaskIDNotSetError(RuntimeError):
    """Harvest task ID not set error."""

    def __init__(self, time_entry: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        """Harvest task ID not set error."""
        super().__init__(
            (
                "Harvest task ID not set for Timing project"
                f" {time_entry['project']['title']}"
            ),
            time_entry,
            *args,
            **kwargs,
        )


def timing_to_harvest_time_entry(time_entry: dict[str, Any]) -> dict[str, Any]:
    """Prepare a time entry for Harvest."""
    try:
        harvest_project_id = get_custom_field_from_project_hierarchy(
            "harvest_project_id", time_entry["project"]
        )
    except CustomFieldNotFoundInHierarchyError as exc:
        raise HarvestProjectIDNotSetError(time_entry) from exc

    try:
        harvest_task_id = get_custom_field_from_project_hierarchy(
            "harvest_task_id", time_entry["project"]
        )
    except CustomFieldNotFoundInHierarchyError as exc:
        raise HarvestTaskIDNotSetError(time_entry) from exc

    return {
        "task_id": harvest_task_id,
        "project_id": harvest_project_id,
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
    }


@timing.command()
@click.option(
    "--harvest-personal-access-token",
    help=(
        "Personal access token for accessing Harvest. Visit"
        " https://id.getharvest.com/developers to get a token."
    ),
    envvar="HARVEST_PERSONAL_ACCESS_TOKEN",
)
@click.option("--harvest-account-id", envvar="HARVEST_ACCOUNT_ID")
@click.pass_obj
def send_to_harvest(
    timing_api: Timing, harvest_personal_access_token: str, harvest_account_id: str
) -> None:
    """Send a time entry to Harvest."""

    def update_harvest_time_entry(time_entry: dict[str, Any]) -> None:
        try:
            harvest_time_entry = harvest_api.get_time_entry(
                time_entry["custom_fields"]["harvest_time_entry_id"]
            )
        except HTTPError as exc:
            if exc.response.status_code == HTTPStatus.NOT_FOUND:
                create_harvest_time_entry(time_entry)
            else:
                raise

        harvest_time_entry = harvest_api.update_time_entry(
            harvest_time_entry["id"], timing_to_harvest_time_entry(time_entry)
        )

    def create_harvest_time_entry(time_entry: dict[str, Any]) -> None:
        harvest_time_entry = harvest_api.create_time_entry(
            timing_to_harvest_time_entry(time_entry)
        )
        timing_api.set_custom_field_in_time_entry(
            time_entry["self"], "harvest_time_entry_id", harvest_time_entry["id"]
        )

    harvest_api = Harvest(harvest_personal_access_token, harvest_account_id)
    for time_entry in timing_api.get_time_entries(load_projects=True):
        if "harvest_time_entry_id" in time_entry["custom_fields"]:
            update_harvest_time_entry(time_entry)
        else:
            create_harvest_time_entry(time_entry)


if __name__ == "__main__":
    load_dotenv()
    main()
