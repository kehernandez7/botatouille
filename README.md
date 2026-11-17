# Botatouille

A small Discord bot built with [discord.py](https://discordpy.readthedocs.io/).

## Features

- **Link fixing:** When someone posts a link whose preview doesn't work well in Discord, the bot reposts the message with a fixed link and deletes the original. The repost shows the author's own name and avatar, and keeps any attachments.

  | Site | Fixed with |
  | --- | --- |
  | X / Twitter | `vxtwitter.com` |
  | TikTok | `tnktok.com` |
  | Reddit | `vxreddit.com` |

  To add a site or switch fixers, edit `LINK_FIXERS` in `cogs/links.py`.

  If the bot doesn't have the **Manage Webhooks** permission in a channel, it reposts as itself instead and tags the author.
- **Server Wrapped:** A recap of what the server listens to on Spotify: top songs, top artists, biggest listeners and the most-replayed song. It's **off until someone with Manage Server turns it on**, and members can opt out at any time. See [Server Wrapped](#server-wrapped).
- **`/mock <prompt>`:** Replies with the text in alternating case, lIkE tHiS.
- **Mock this message:** Right-click (or long-press) any message, then **Apps → Mock this message**.

## Server Wrapped

Nothing is logged until someone with the **Manage Server** permission runs `/wrapped start`. The bot then posts a public message saying what it logs and how to opt out.

It reads the **Listening to Spotify** status Discord already shows, so it only sees members who have Spotify connected and shown on their Discord profile. For each song someone listens to for at least 30 seconds, it stores the song, artists, album, how long they listened and when. The data is stored per server.

| Command | Who can use it | What it does |
| --- | --- | --- |
| `/wrapped start` | Manage Server | Starts logging and announces it in the channel |
| `/wrapped stop [delete_data]` | Manage Server | Stops logging. Keeps the data for recaps unless `delete_data` is on |
| `/wrapped recap [period]` | Anyone | Posts the recap for this month, this year or all time |
| `/wrapped optout` | Anyone | Stops logging you in every server and deletes everything logged about you |
| `/wrapped optin` | Anyone | Undoes an opt-out |
| `/wrapped status` | Anyone | Privately shows whether the server is logging and how many of your listens are stored |

If the bot is removed from a server, it deletes everything it logged there.

Pausing a song partway through can count it twice, because Discord drops the status while paused.

## Requirements

- Python 3.12 (the version Railway uses, set in `.python-version`). 3.9+ also works locally.
- A Discord bot application with the **Message Content** intent enabled

## Setup

1. **Create the bot in Discord**
   1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
   2. Under **Bot**, click **Reset Token** and copy the token, then turn on **Presence Intent**, **Server Members Intent** and **Message Content Intent**. Server Wrapped needs the first two. The bot won't connect if any of the three are off.
   3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes. Give it the **Send Messages**, **Manage Messages** (to delete the original message), **Manage Webhooks** (to repost as the author), **Attach Files**, **Add Reactions** and **Read Message History** permissions, then open the generated URL to invite the bot to your server.

2. **Install dependencies**

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

3. **Set the bot token**

   ```sh
   export DISCORD_BOT_SECRET=your-bot-token
   ```

   Use the token from the **Bot** page. The Application ID, Public Key and Client Secret won't work.

   Optionally, set this too:

   | Variable | What it's for |
   | --- | --- |
   | `WRAPPED_DB_PATH` | Where Server Wrapped keeps its SQLite database. Defaults to `wrapped.db` in the current folder. |

## Running

```sh
python main.py
```

The bot logs `Logged in as <bot name>` when it connects.

### Syncing slash commands

Slash commands are registered with Discord separately from the bot running. After you add or change one and deploy, the bot's owner sends this in any channel the bot can read:

```
!sync
```

Only the owner of the Discord application can run it; anyone else is ignored.

## Deploying

The bot runs on [Railway](https://railway.app), which picks up `requirements.txt` and `.python-version` automatically. Set `DISCORD_BOT_SECRET` in the service's **Variables** tab, and use `python main.py` as the start command.

Railway wipes the service's files on every deploy, so Server Wrapped needs a [volume](https://docs.railway.com/reference/volumes) to keep its data. Add a volume to the service (for example, mounted at `/data`), and set `WRAPPED_DB_PATH` to `/data/wrapped.db`.

## Development

Lint and format with [Ruff](https://docs.astral.sh/ruff/). GitHub Actions runs the same checks on every pull request.

```sh
ruff check .
ruff format .
```

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | Creates the bot, loads the cogs, logging and error handling |
| `cogs/links.py` | Link fixing |
| `cogs/wrapped.py` | Server Wrapped |
| `cogs/fun.py` | `/mock` and the **Mock this message** menu option |
| `cogs/admin.py` | Owner-only `!sync` |
| `requirements.txt` | Runtime dependencies |
| `requirements-dev.txt` | Runtime dependencies plus Ruff |
| `pyproject.toml` | Ruff settings |
