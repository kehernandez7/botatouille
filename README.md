# Botatouille

A small Discord bot built with [discord.py](https://discordpy.readthedocs.io/).

## Features

- **Better X embeds:** When someone posts an `x.com` link, the bot deletes the message and reposts it, tagging the author, with the link changed to `vxtwitter.com` so it embeds properly. If the original message was a reply, the repost is a reply too.
- **`/mock <prompt>`:** Replies with the text in alternating case, lIkE tHiS.

## Requirements

- Python 3.12 (the version Railway uses, set in `.python-version`). 3.9+ also works locally.
- A Discord bot application with the **Message Content** intent enabled

## Setup

1. **Create the bot in Discord**
   1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
   2. Under **Bot**, click **Reset Token** and copy the token, then turn on **Message Content Intent**.
   3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes. Give it the **Send Messages**, **Manage Messages** (to delete the original message), **Add Reactions** and **Read Message History** permissions, then open the generated URL to invite the bot to your server.

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
| `cogs/links.py` | Reposts `x.com` links as `vxtwitter.com` |
| `cogs/fun.py` | `/mock` |
| `cogs/admin.py` | Owner-only `!sync` |
| `requirements.txt` | Runtime dependencies |
| `requirements-dev.txt` | Runtime dependencies plus Ruff |
| `pyproject.toml` | Ruff settings |
