# Botatouille

A small Discord bot built with [discord.py](https://discordpy.readthedocs.io/).

## Features

- **Better X embeds:** When someone posts an `x.com` link, the bot deletes the message and reposts it, tagging the author, with the link changed to `vxtwitter.com` so it embeds properly. If the original message was a reply, the repost is a reply too.
- **`/mock <prompt>`:** Replies with the text in alternating case, lIkE tHiS.

## Requirements

- Python 3.9+
- A Discord bot application with the **Message Content** intent enabled

## Setup

1. **Create the bot in Discord**
   1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create an application.
   2. Under **Bot**, copy the token and turn on **Message Content Intent**.
   3. Under **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes. Give it the **Send Messages**, **Manage Messages** (to delete the original message), **Add Reactions** and **Read Message History** permissions, then open the generated URL to invite the bot to your server.

2. **Install dependencies**

   ```sh
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Set the bot token**

   ```sh
   export DISCORD_BOT_SECRET=your-bot-token
   ```

## Running

```sh
python main.py
```

The bot prints `I'm in as <bot name>` when it connects and syncs its slash commands. A new slash command can take a little while to show up in Discord.

`main.py` also starts a tiny Flask web server (`keep_alive.py`) on a random port between 2000 and 9000. It's for hosts that put a bot to sleep unless it's serving web traffic. You don't need it for local development.

## Project structure

| File | Purpose |
| --- | --- |
| `main.py` | Bot setup, the link-rewriting message handler and the `/mock` command |
| `keep_alive.py` | Background Flask server that keeps the bot awake on some hosts |
| `requirements.txt` | Python dependencies |
