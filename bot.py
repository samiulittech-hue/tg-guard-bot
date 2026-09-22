import os
import json
import threading
from flask import Flask
import telebot

BOT_TOKEN = "8834320489:AAECc90hTXDSmkwH3DH4CGPoFQCSatSbltQ"
REQUIRED_ADDS = 3
DATA_FILE = "group_users.json"

bot = telebot.TeleBot(BOT_TOKEN)

# Mini Web Server for Render Keep-Alive
app = Flask(__name__)

@app.route('/')
def home():
    return "Guard Bot is Active 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Data Functions
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error: {e}")

group_users = load_data()

def get_user_stats(user_id):
    str_uid = str(user_id)
    if str_uid not in group_users:
        group_users[str_uid] = {"added_count": 0, "is_unlocked": False}
        save_data(group_users)
    return group_users[str_uid]

# Private Start Command Handler
@bot.message_handler(commands=['start'], func=lambda msg: msg.chat.type == 'private')
def send_welcome(message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"👋 হ্যালো **{user_name}**!\n\n"
        f"🤖 আমি **Group Access Guard Bot**।\n"
        f"গ্রুপে স্প্যাম ঠেকাতে এবং মেম্বার বাড়ানোর জন্য আমাকে আপনার গ্রুপে **Admin** হিসেবে যুক্ত করুন "
        f"(অবশ্যই **Delete Messages** পারমিশন অন রাখবেন)।\n\n"
        f"📌 নিয়ম: সদস্যরা ন্যূনতম ৩ জন নতুন মেম্বার অ্যাড না করা পর্যন্ত গ্রুপে মেসেজ লিখতে পারবে না।"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

# Track Newly Added Members
@bot.message_handler(content_types=['new_chat_members'])
def handle_new_members(message):
    adder_id = message.from_user.id
    adder_name = message.from_user.first_name
    chat_id = message.chat.id

    new_users = [u for u in message.new_chat_members if not u.is_bot]
    added_amount = len(new_users)

    if added_amount > 0:
        stats = get_user_stats(adder_id)
        stats["added_count"] += added_amount
        if stats["added_count"] >= REQUIRED_ADDS:
            stats["is_unlocked"] = True
        save_data(group_users)
        remaining = max(0, REQUIRED_ADDS - stats["added_count"])

        if stats["is_unlocked"]:
            bot.send_message(
                chat_id,
                f"🎉 **Access Unlocked!**\n\n👤 Member: **{adder_name}**\n✅ Added: **{stats['added_count']}/{REQUIRED_ADDS}**\n💬 You can now send messages!",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(
                chat_id,
                f"➕ **Member Added!**\n\n👤 Member: **{adder_name}**\n📊 Progress: **{stats['added_count']}/{REQUIRED_ADDS}**\n⏳ Add **{remaining} more** to unlock.",
                parse_mode="Markdown"
            )

# Group Message Filter
@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def monitor_group_messages(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        if chat_member.status in ['administrator', 'creator']:
            return
    except Exception:
        pass

    stats = get_user_stats(user_id)
    if not stats["is_unlocked"]:
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass

        remaining = REQUIRED_ADDS - stats["added_count"]
        warning_msg = (
            f"🚫 **Chat Locked!**\n\nHey **{user_name}**, add **{REQUIRED_ADDS} members** before texting.\n"
            f"📊 Added: **{stats['added_count']}/{REQUIRED_ADDS}** (Need **{remaining}** more)"
        )
        sent = bot.send_message(chat_id, warning_msg, parse_mode="Markdown")
        try:
            bot.delete_message(chat_id, sent.message_id, timeout=8)
        except Exception:
            pass

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    print("Bot polling started...")
    bot.infinity_polling()
