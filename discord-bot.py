import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BOT_TOKEN = "YOUR_DISCORD_TOKEN_HERE"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

CROPS = {
    "Potato":     {"time": 60,   "emoji": "🥔"},
    "Tomato":     {"time": 15,   "emoji": "🍅"},
    "Lettuce":    {"time": 480,  "emoji": "🥬"},
    "Wheat":      {"time": 240,  "emoji": "🌾"},
    "Pineapple":  {"time": 30,   "emoji": "🍍"},
    "Carrot":     {"time": 120,  "emoji": "🥕"},
    "Strawberry": {"time": 360,  "emoji": "🍓"},
    "Corn":       {"time": 720,  "emoji": "🌽"},
    "Grape":      {"time": 600,  "emoji": "🍇"},
    "Eggplant":   {"time": 300,  "emoji": "🍆"},
    "Tea":        {"time": 45,   "emoji": "🍵"},
    "Cacao":      {"time": 300,  "emoji": "🍫"},
    "Avocado":    {"time": 780,  "emoji": "🥑"},
}

# { user_id: { crop: { "finish": datetime, "warned": bool, "channel_id": int } } }
active_timers = {}


def get_warning_minutes(crop_duration_minutes):
    if crop_duration_minutes < 15:
        return None
    elif crop_duration_minutes < 60:
        return 3
    else:
        return 5


def format_time_left(minutes_left):
    if minutes_left <= 0:
        return "✅ Ready!"
    hours = int(minutes_left // 60)
    mins = int(minutes_left % 60)
    if hours > 0:
        return f"{hours}h {mins}min"
    return f"{mins}min"


# ── Background checker ─────────────────────────────────────────────
@tasks.loop(seconds=30)
async def timer_checker():
    now = datetime.now()
    for user_id, crops in list(active_timers.items()):
        for crop, data in list(crops.items()):
            finish = data["finish"]
            channel_id = data["channel_id"]
            warned = data["warned"]
            crop_duration = CROPS[crop]["time"]
            emoji = CROPS[crop]["emoji"]
            warn_minutes = get_warning_minutes(crop_duration)
            minutes_left = (finish - now).total_seconds() / 60

            channel = bot.get_channel(channel_id)
            if not channel:
                continue

            # Send warning ping
            if warn_minutes and not warned and 0 < minutes_left <= warn_minutes:
                await channel.send(
                    f"⚠️ <@{user_id}> **{crop}** {emoji} is almost ready!\n"
                    f"⏱ **{int(minutes_left)} min** left!"
                )
                active_timers[user_id][crop]["warned"] = True

            # Send ready ping
            if minutes_left <= 0:
                await channel.send(
                    f"🎉 <@{user_id}> **{crop}** {emoji} is ready to harvest!"
                )
                del active_timers[user_id][crop]


# ── Crop dropdown ──────────────────────────────────────────────────
class CropSelect(discord.ui.Select):
    def __init__(self, channel_id):
        self.channel_id = channel_id
        options = []
        for crop, info in CROPS.items():
            duration = format_time_left(info["time"])
            options.append(discord.SelectOption(
                label=f"{crop} ({duration})",
                value=crop,
                emoji=info["emoji"]
            ))
        super().__init__(
            placeholder="🌱 Pick a crop...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        crop_name = self.values[0]
        user_id = interaction.user.id
        info = CROPS[crop_name]

        finish_time = datetime.now() + timedelta(minutes=info["time"])

        if user_id not in active_timers:
            active_timers[user_id] = {}

        active_timers[user_id][crop_name] = {
            "finish": finish_time,
            "warned": False,
            "channel_id": self.channel_id
        }

        duration_str = format_time_left(info["time"])
        await interaction.response.send_message(
            f"{info['emoji']} **{crop_name}** timer started!\n"
            f"⏱ Ready in **{duration_str}**\n"
            f"I'll ping you here when it's ready!",
            ephemeral=True
        )


class CropView(discord.ui.View):
    def __init__(self, channel_id):
        super().__init__(timeout=60)
        self.add_item(CropSelect(channel_id))


# ── Slash commands ─────────────────────────────────────────────────
@bot.tree.command(name="settime", description="Start a crop timer")
async def settime(interaction: discord.Interaction):
    view = CropView(interaction.channel_id)
    await interaction.response.send_message(
        "🌾 **Pick a crop to start its timer:**",
        view=view,
        ephemeral=True
    )


@bot.tree.command(name="mytime", description="Check time remaining on your crops")
async def mytime(interaction: discord.Interaction):
    user_id = interaction.user.id
    timers = active_timers.get(user_id, {})

    if not timers:
        await interaction.response.send_message(
            "🌱 No active crop timers!\nUse `/settime` to start one.",
            ephemeral=True
        )
        return

    now = datetime.now()
    lines = ["🌾 **Your Active Crops:**\n"]
    ready_crops = []

    for crop, data in sorted(timers.items(), key=lambda x: x[1]["finish"]):
        info = CROPS[crop]
        minutes_left = (data["finish"] - now).total_seconds() / 60
        time_str = format_time_left(minutes_left)
        lines.append(f"{info['emoji']} **{crop}** — {time_str}")
        if minutes_left <= 0:
            ready_crops.append(crop)

    if ready_crops:
        lines.append("\n🎉 **Ready to harvest:**")
        for crop in ready_crops:
            lines.append(f"{CROPS[crop]['emoji']} {crop}")

    await interaction.response.send_message("\n".join(lines), ephemeral=True)


@bot.tree.command(name="clear", description="Clear all your active crop timers")
async def clear(interaction: discord.Interaction):
    active_timers[interaction.user.id] = {}
    await interaction.response.send_message("🗑 All your crop timers have been cleared!", ephemeral=True)


# ── Startup ────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.tree.sync()
    timer_checker.start()
    print(f"🤖 Logged in as {bot.user} — Bot is running!")


bot.run(BOT_TOKEN)
