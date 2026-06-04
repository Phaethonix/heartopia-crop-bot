import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import threading
import time
import logging
import re

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
    "Eggplant":   {"time": 420,  "emoji": "🍆"},
    "Tea":        {"time": 45,   "emoji": "🍵"},
    "Cacao":      {"time": 300,  "emoji": "🍫"},
    "Avocado":    {"time": 780,  "emoji": "🥑"},
}

# { user_id: { timer_key: { crop, finish, warned, chat_id, duration_minutes } } }
active_timers = {}

# { user_id: { "action": "custom_time" | "replace_or_add", "crop": str, "chat_id": int } }
user_state = {}


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


def parse_custom_time(text):
    """Parse user input like '5h 33m', '2h', '45m', '1h30m' into minutes. Returns None if invalid."""
    text = text.strip().lower()
    # Try natural format: 5h 33m / 1h30m / 2h / 45m
    pattern = r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m)?"
    match = re.fullmatch(pattern, text)
    if match and (match.group(1) or match.group(2)):
        hours = int(match.group(1) or 0)
        mins = int(match.group(2) or 0)
        total = hours * 60 + mins
        return total if total > 0 else None
    return None


def get_next_timer_key(user_id, crop_name):
    """Generate a unique key like Grape, Grape#2, Grape#3 etc."""
    timers = active_timers.get(user_id, {})
    if crop_name not in timers:
        return crop_name
    i = 2
    while f"{crop_name}#{i}" in timers:
        i += 1
    return f"{crop_name}#{i}"


def add_timer(user_id, crop_name, chat_id, duration_minutes, key=None):
    """Add a timer entry for a user."""
    if user_id not in active_timers:
        active_timers[user_id] = {}
    timer_key = key if key else get_next_timer_key(user_id, crop_name)
    active_timers[user_id][timer_key] = {
        "crop": crop_name,
        "finish": datetime.now() + timedelta(minutes=duration_minutes),
        "warned": False,
        "chat_id": chat_id,
        "duration_minutes": duration_minutes,
    }
    return timer_key


def crop_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for crop, info in CROPS.items():
        duration = format_time_left(info["time"])
        buttons.append(InlineKeyboardButton(
            text=f"{info['emoji']} {crop} ({duration})",
            callback_data=f"start_{crop}"
        ))
    buttons.append(InlineKeyboardButton(
        text="⏱ Custom Time",
        callback_data="custom_time"
    ))
    markup.add(*buttons)
    return markup


def replace_or_add_keyboard(crop_name):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Replace existing", callback_data=f"replace_{crop_name}"),
        InlineKeyboardButton("➕ Add new timer", callback_data=f"addnew_{crop_name}")
    )
    return markup


# ── Background checker ─────────────────────────────────────────────
def timer_checker():
    while True:
        now = datetime.now()
        for user_id, timers in list(active_timers.items()):
            for key, data in list(timers.items()):
                finish = data["finish"]
                chat_id = data["chat_id"]
                warned = data["warned"]
                crop_name = data["crop"]
                crop_duration = data["duration_minutes"]
                emoji = CROPS[crop_name]["emoji"]
                warn_minutes = get_warning_minutes(crop_duration)
                minutes_left = (finish - now).total_seconds() / 60

                # Warning ping
                if warn_minutes and not warned and 0 < minutes_left <= warn_minutes:
                    try:
                        bot.send_message(
                            chat_id,
                            f"⚠️ *{key}* {emoji} is almost ready!\n"
                            f"⏱ *{int(minutes_left)} min* left!",
                            parse_mode="Markdown"
                        )
                        active_timers[user_id][key]["warned"] = True
                    except Exception as e:
                        logging.error(f"Warning ping error: {e}")

                # Ready ping
                if minutes_left <= 0:
                    try:
                        bot.send_message(
                            chat_id,
                            f"🎉 *{key}* {emoji} is ready to harvest!",
                            parse_mode="Markdown"
                        )
                        del active_timers[user_id][key]
                    except Exception as e:
                        logging.error(f"Ready ping error: {e}")

        time.sleep(30)


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

    # Check if this crop already has a timer
    timers = active_timers.get(user_id, {})
    if crop_name in timers:
        # Ask replace or add new
        user_state[user_id] = {
            "action": "replace_or_add",
            "crop": crop_name,
            "chat_id": call.message.chat.id,
            "duration_minutes": CROPS[crop_name]["time"]
        }
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"{CROPS[crop_name]['emoji']} *{crop_name}* already has a timer running!\n"
            f"What would you like to do?",
            reply_markup=replace_or_add_keyboard(crop_name),
            parse_mode="Markdown"
        )
        return

    # No existing timer — start immediately
    info = CROPS[crop_name]
    timer_key = add_timer(user_id, crop_name, call.message.chat.id, info["time"])
    duration_str = format_time_left(info["time"])

    bot.answer_callback_query(call.id, f"{info['emoji']} Timer started!")
    bot.send_message(
        call.message.chat.id,
        f"{info['emoji']} *{timer_key}* timer started!\n"
        f"⏱ Ready in *{duration_str}*\n\n"
        f"Pick another crop or use /mytime to check progress.",
        parse_mode="Markdown",
        reply_markup=crop_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("replace_"))
def replace_timer(call):
    crop_name = call.data.replace("replace_", "")
    user_id = call.from_user.id
    info = CROPS[crop_name]
    chat_id = call.message.chat.id

    # Get duration from state if custom, else use default
    state = user_state.get(user_id, {})
    duration = state.get("duration_minutes", info["time"])

    add_timer(user_id, crop_name, chat_id, duration, key=crop_name)
    user_state.pop(user_id, None)

    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id,
        f"{info['emoji']} *{crop_name}* timer replaced!\n"
        f"⏱ Ready in *{format_time_left(duration)}*",
        parse_mode="Markdown",
        reply_markup=crop_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("addnew_"))
def addnew_timer(call):
    crop_name = call.data.replace("addnew_", "")
    user_id = call.from_user.id
    info = CROPS[crop_name]
    chat_id = call.message.chat.id

    state = user_state.get(user_id, {})
    duration = state.get("duration_minutes", info["time"])

    timer_key = add_timer(user_id, crop_name, chat_id, duration)
    user_state.pop(user_id, None)

    bot.answer_callback_query(call.id)
    bot.send_message(
        chat_id,
        f"{info['emoji']} *{timer_key}* timer added!\n"
        f"⏱ Ready in *{format_time_left(duration)}*",
        parse_mode="Markdown",
        reply_markup=crop_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == "custom_time")
def custom_time_start(call):
    user_id = call.from_user.id
    user_state[user_id] = {
        "action": "awaiting_crop",
        "chat_id": call.message.chat.id
    }
    bot.answer_callback_query(call.id)

    # Show crop selection for custom time
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for crop, info in CROPS.items():
        buttons.append(InlineKeyboardButton(
            text=f"{info['emoji']} {crop}",
            callback_data=f"customcrop_{crop}"
        ))
    markup.add(*buttons)

    bot.send_message(
        call.message.chat.id,
        "⏱ *Custom time — pick a crop first:*",
        reply_markup=markup,
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("customcrop_"))
def custom_time_crop_selected(call):
    crop_name = call.data.replace("customcrop_", "")
    user_id = call.from_user.id

    user_state[user_id] = {
        "action": "awaiting_custom_time",
        "crop": crop_name,
        "chat_id": call.message.chat.id
    }

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"{CROPS[crop_name]['emoji']} *{crop_name}* selected!\n\n"
        f"Enter your custom time:\n"
        f"• `5h 33m`\n"
        f"• `2h`\n"
        f"• `45m`\n"
        f"• `1h30m`",
        parse_mode="Markdown"
    )


@bot.message_handler(func=lambda message: (
    message.from_user.id in user_state and
    user_state[message.from_user.id].get("action") == "awaiting_custom_time"
))
def receive_custom_time(message):
    user_id = message.from_user.id
    state = user_state[user_id]
    crop_name = state["crop"]
    chat_id = state["chat_id"]
    info = CROPS[crop_name]

    total_minutes = parse_custom_time(message.text)

    if total_minutes is None:
        bot.send_message(
            chat_id,
            "❌ Couldn't read that time. Try formats like:\n"
            "`5h 33m` · `2h` · `45m` · `1h30m`",
            parse_mode="Markdown"
        )
        return

    # Check if crop already has a timer
    timers = active_timers.get(user_id, {})
    if crop_name in timers:
        user_state[user_id] = {
            "action": "replace_or_add",
            "crop": crop_name,
            "chat_id": chat_id,
            "duration_minutes": total_minutes
        }
        bot.send_message(
            chat_id,
            f"{info['emoji']} *{crop_name}* already has a timer!\nWhat would you like to do?",
            reply_markup=replace_or_add_keyboard(crop_name),
            parse_mode="Markdown"
        )
        return

    timer_key = add_timer(user_id, crop_name, chat_id, total_minutes)
    user_state.pop(user_id, None)

    bot.send_message(
        chat_id,
        f"{info['emoji']} *{timer_key}* custom timer started!\n"
        f"⏱ Ready in *{format_time_left(total_minutes)}*",
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

    for key, data in sorted(timers.items(), key=lambda x: x[1]["finish"]):
        crop_name = data["crop"]
        info = CROPS[crop_name]
        minutes_left = (data["finish"] - now).total_seconds() / 60
        time_str = format_time_left(minutes_left)
        lines.append(f"{info['emoji']} *{key}* — {time_str}")
        if minutes_left <= 0:
            ready_crops.append(key)

    if ready_crops:
        lines.append("\n🎉 *Ready to harvest:*")
        for key in ready_crops:
            lines.append(f"{CROPS[active_timers[user_id][key]['crop']]['emoji']} {key}")

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

