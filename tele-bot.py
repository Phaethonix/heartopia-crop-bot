import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

BOT_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE"
bot = telebot.TeleBot(BOT_TOKEN)

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

# { user_id: { crop: { "finish": datetime, "warned": bool, "chat_id": int } } }
active_timers = {}


def get_warning_minutes(crop_duration_minutes):
    """Return how many minutes before ready to warn. None = no warning."""
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


def crop_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for crop, info in CROPS.items():
        duration = format_time_left(info["time"])
        buttons.append(InlineKeyboardButton(
            text=f"{info['emoji']} {crop} ({duration})",
            callback_data=f"start_{crop}"
        ))
    markup.add(*buttons)
    return markup


# ── Background checker ─────────────────────────────────────────────
def timer_checker():
    while True:
        now = datetime.now()
        for user_id, crops in list(active_timers.items()):
            for crop, data in list(crops.items()):
                finish = data["finish"]
                chat_id = data["chat_id"]
                warned = data["warned"]
                crop_duration = CROPS[crop]["time"]
                emoji = CROPS[crop]["emoji"]
                warn_minutes = get_warning_minutes(crop_duration)
                minutes_left = (finish - now).total_seconds() / 60

                # Send warning ping
                if warn_minutes and not warned and 0 < minutes_left <= warn_minutes:
                    try:
                        bot.send_message(
                            chat_id,
                            f"⚠️ *{crop}* {emoji} is almost ready!\n"
                            f"⏱ *{int(minutes_left)} min* left!",
                            parse_mode="Markdown"
                        )
                        active_timers[user_id][crop]["warned"] = True
                    except Exception as e:
                        logging.error(f"Warning ping error: {e}")

                # Send ready ping
                if minutes_left <= 0:
                    try:
                        bot.send_message(
                            chat_id,
                            f"🎉 *{crop}* {emoji} is ready to harvest!",
                            parse_mode="Markdown"
                        )
                        del active_timers[user_id][crop]
                    except Exception as e:
                        logging.error(f"Ready ping error: {e}")

        time.sleep(30)  # check every 30 seconds


# ── Handlers ───────────────────────────────────────────────────────
@bot.message_handler(commands=["settime"])
def settime_command(message):
    bot.send_message(
        message.chat.id,
        "🌱 *Pick a crop to start its timer:*",
        reply_markup=crop_keyboard(),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("start_"))
def start_timer(call):
    crop_name = call.data.replace("start_", "")
    user_id = call.from_user.id

    if crop_name not in CROPS:
        bot.answer_callback_query(call.id, "Unknown crop!")
        return

    info = CROPS[crop_name]
    finish_time = datetime.now() + timedelta(minutes=info["time"])

    if user_id not in active_timers:
        active_timers[user_id] = {}

    active_timers[user_id][crop_name] = {
        "finish": finish_time,
        "warned": False,
        "chat_id": call.message.chat.id
    }

    duration_str = format_time_left(info["time"])
    bot.answer_callback_query(call.id, f"{info['emoji']} Timer started!")
    bot.send_message(
        call.message.chat.id,
        f"{info['emoji']} *{crop_name}* timer started!\n"
        f"⏱ Ready in *{duration_str}*\n\n"
        f"Pick another crop or use /mytime to check progress.",
        parse_mode="Markdown",
        reply_markup=crop_keyboard()
    )


@bot.message_handler(commands=["mytime"])
def show_timers(message):
    user_id = message.from_user.id
    timers = active_timers.get(user_id, {})

    if not timers:
        bot.send_message(message.chat.id, "🌱 No active crop timers!\nUse /settime to start one.")
        return

    now = datetime.now()
    lines = ["🌾 *Your Active Crops:*\n"]
    ready_crops = []

    for crop, data in sorted(timers.items(), key=lambda x: x[1]["finish"]):
        info = CROPS[crop]
        minutes_left = (data["finish"] - now).total_seconds() / 60
        time_str = format_time_left(minutes_left)
        lines.append(f"{info['emoji']} *{crop}* — {time_str}")
        if minutes_left <= 0:
            ready_crops.append(crop)

    if ready_crops:
        lines.append("\n🎉 *Ready to harvest:*")
        for crop in ready_crops:
            lines.append(f"{CROPS[crop]['emoji']} {crop}")

    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["clear"])
def clear_timers(message):
    active_timers[message.from_user.id] = {}
    bot.send_message(message.chat.id, "🗑 All your crop timers have been cleared!")


# ── Start ──────────────────────────────────────────────────────────
checker_thread = threading.Thread(target=timer_checker, daemon=True)
checker_thread.start()

print("🤖 Bot is running...")
bot.infinity_polling()
