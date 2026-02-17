Scripts I use to manage my timesheets.

You're welcome to use or hack at them as much as you like!

```
❯ uv run timesheets.py
Usage: timesheets.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  harvest
  timing
```

## Harvest

Reads clients, projects, and tasks from Harvest.

The Timing script also creates and updates time entries in Harvest based on Timing time entries.

```
❯ uv run timesheets.py
Usage: timesheets.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  harvest
  timing

timesheets on  uv [✘34?7] via  v3.14.2 (timesheet)
❯ uv run timesheets.py harvest
Usage: timesheets.py harvest [OPTIONS] COMMAND [ARGS]...

Options:
  --personal-access-token TEXT  Personal access token for accessing Harvest.
                                Visit https://id.getharvest.com/developers to
                                get a token.
  --account-id TEXT
  --help                        Show this message and exit.

Commands:
  list-tasks
```

## Timing

Reads projects from [Timing](https://timingapp.com). Also associates projects with Harvest projects and tasks, and sends time entries to Harvest based on those associations.

```
❯ uv run timesheets.py timing
Usage: timesheets.py timing [OPTIONS] COMMAND [ARGS]...

Options:
  --personal-access-token TEXT  Personal access token for accessing Timing.
                                Visit
                                https://web.timingapp.com/integrations/tokens
                                to get a token.
  --help                        Show this message and exit.

Commands:
  list-projects
  send-to-harvest
  set-harvest-project-id  Set Harvest project ID in Timing project.
  set-harvest-task-id     Set Harvest task ID in Timing project.
```
