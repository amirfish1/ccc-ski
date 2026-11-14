# Ski: a season planner for Claude Command Center

One page for a ski season: the snow forecast, pass blackout dates, every
weekend and holiday as a row, who is going, places to stay, and reminders
before a booking stops being refundable. An agent sits next to the page; you
tell it what to change in plain words.

It comes set up for Palisades Tahoe with the Ikon Base Pass, 2026-27 season.
The agent can change the resort, the pass, the dates and the people.

## What you can ask the agent

- Change a weekend's dates
- Change who is going
- Record a booking (it then reminds you before free cancellation ends)
- Search for hotels and Airbnbs for a weekend

It never logs in, books or pays. It finds options and links; you book.

## Install

You need [Claude Command Center](https://github.com/amirfish1/claude-command-center)
running, and an agent it can start (Claude Code, for example).

Copy the `ski` folder into CCC's apps folder. The folder must be named `ski`.

```bash
mkdir -p ~/.claude/command-center/apps
cp -R ski ~/.claude/command-center/apps/ski
```

Reload CCC and open **Ski** in the left rail.

The first time it runs, the Setup routine installs two open source search
tools into the app's own folder (`ski/.venv`): `stays` (Google Hotels) and
`pyairbnb` (Airbnb). Nothing is installed anywhere else. Hotel search needs
Python 3.10 or newer; a Mac's built-in Python is older, so install Python from
python.org first if Setup says so. Everything else works without it.

## Your data stays on your machine

Your ticks, notes and bookings are plain files in the app's folder. Nothing is
sent anywhere except the searches the agent runs for you.
