# Heartopia Crop Bot

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Discord](https://img.shields.io/badge/Discord-7289DA?logo=discord&logoColor=white)](https://discord.com)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?logo=telegram&logoColor=white)](https://telegram.org)

An automation bot for the game **Heartopia** that tracks crop growth cycles and sends you pings when your harvest is ready.

Supports both **Discord** (via Slash Commands) and **Telegram**, so you never miss a harvest timer regardless of your platform.

---

## Features

- **Crop Tracking:** Start timers for any crop in Heartopia.
- **Automated Pings:** Get notified when your crops are almost ready and when they're done.
- **Clear Timers:** Wipe all active timers with a single command.
- **Dual Platform:**
  - **Discord:** Interactive Slash Commands (`/settime`, `/mytime`, `/clear`).
  - **Telegram:** Inline keyboard buttons (`/settime`, `/mytime`, `/clear`).

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8 or higher**
- **pip** (Python package installer)

You will also need to create bot accounts on both platforms:

1. [Discord Developer Portal](https://discord.com/developers/applications)
2. [BotFather](https://t.me/botfather) on Telegram

---

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Phaethonix/heartopia-crop-bot.git
   cd heartopia-crop-bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux / macOS
   venv\Scripts\activate         # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Add your bot tokens**

### Telegram
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the token and paste it into `tele-bot.py`:
   ```python
   BOT_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE"
   ```

### Discord
1. Go to https://discord.com/developers/applications
2. Click **New Application** → give it a name
3. Go to the **Bot** tab → click **Reset Token** → copy it
4. Paste it into `discord-bot.py`:
   ```python
   BOT_TOKEN = "YOUR_DISCORD_TOKEN_HERE"
   ```
5. Navigate to the **OAuth2 → URL Generator** tab:
   - **Scopes:** `bot`, `applications.commands`
   - **Bot Permissions:** `Send Messages`, `Use Slash Commands`
6. Copy the generated URL and paste it into your browser to invite the bot to your server.

---

## Usage

### Running the bots

**Discord:**
```bash
python discord-bot.py
```

**Telegram:**
```bash
python tele-bot.py
```

### Commands

#### Discord (Slash Commands)
Type `/` in your server to see available commands.

| Command | Description |
| :--- | :--- |
| `/settime` | Opens a dropdown to start a timer for a crop |
| `/mytime` | Shows all your active crop timers and time remaining |
| `/clear` | Clears all your active crop timers |

#### Telegram
Send these as direct messages to the bot.

| Command | Description |
| :--- | :--- |
| `/settime` | Opens an inline keyboard to start a crop timer | 
|(Telegram Only)| custom timers, multiple timer for same crops |
| `/mytime` | Lists all your active crop timers and time remaining |
| `/clear` | Clears all your active crop timers |

---

## Supported Crops

| Crop | Timer |
| :--- | :--- |
| 🍅 Tomato | 15 min |
| 🍵 Tea | 45 min |
| 🍍 Pineapple | 30 min |
| 🥔 Potato | 1h |
| 🥕 Carrot | 2h |
| 🌾 Wheat | 4h |
| 🍆 Eggplant | 7h |
| 🍫 Cacao | 5h |
| 🍓 Strawberry | 6h |
| 🍇 Grape | 10h |
| 🌽 Corn | 12h |
| 🥬 Lettuce | 8h |
| 🥑 Avocado | 13h |

---

## Files

```
discord-bot.py      # Discord bot
tele-bot.py         # Telegram bot
requirements.txt    # Python dependencies
README.md           # You are here
```
