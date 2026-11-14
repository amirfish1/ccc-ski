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

One line installs Claude Command Center, adds Ski and opens it. The rest of
Claude Command Center stays out of the way behind a "More" button.

```bash
curl -fsSL https://raw.githubusercontent.com/amirfish1/claude-command-center/main/scripts/install.sh | CCC_APP=amirfish1/ccc-ski bash
```

Already have Claude Command Center? Run `ccc app install amirfish1/ccc-ski --focus`
(leave out `--focus` to keep your usual view).

You also need an agent it can start, for example Claude Code. The page works
without one; the agent is what changes it for you.

The first time it runs, the Setup routine installs two open source search
tools into the app's own folder: `stays` (Google Hotels) and `pyairbnb`
(Airbnb). They need Python 3.10 or newer. If the computer's Python is older
(a Mac's built-in one is), Setup downloads a private Python into the same
folder with `uv`. Nothing is installed anywhere else, and everything except
hotel search works without it.

## Your data stays on your machine

Your ticks, notes and bookings are plain files in the app's folder. Nothing is
sent anywhere except the searches the agent runs for you.
