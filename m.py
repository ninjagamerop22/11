import os
import re
import subprocess
import telebot
from threading import Timer
import time
import ipaddress
import logging
import random
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Initialize logging for better monitoring
logging.basicConfig(filename='bot_actions.log', level=logging.INFO, 
                    format='%(asctime)s - %(message)s')

# Initialize the bot with the token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("Please set your bot token in the environment variables!")

bot = telebot.TeleBot(TOKEN)

# List of authorized user IDs
AUTHORIZED_USERS = [5113311276, 6800732852]  # Replace with actual user chat IDs

# Regex pattern to match the IP, port, and duration
pattern = re.compile(r"(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\s(\d{1,5})\s(\d+)")

# Dictionary to keep track of subprocesses and timers
processes = {}

# Dictionary to store user modes (manual or auto)
user_modes = {}

# Helper function to validate IP
def is_valid_ip(ip):
    try:
        ip_obj = ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

# Validate port
def is_valid_port(port):
    return 1 <= int(port) <= 65535

# Validate duration
def is_valid_duration(duration):
    return int(duration) > 0 and int(duration) <= 600  # like max 1 hour

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Create the button markup
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    manual_button = KeyboardButton('Manual Mode')
    auto_button = KeyboardButton('Auto Mode')
    markup.add(manual_button, auto_button)

    welcome_text = (
        "👋 *Hey there! Welcome to Action Bot!*\n\n"
        "I'm here to help you manage actions easily and efficiently. 🚀\n\n"
        "🔹 To *start* an action, you can choose between:\n"
        "1. `Manual Mode`: Enter IP, port, and duration manually.\n"
        "2. `Auto Mode`: Enter IP and port, and I'll choose a random duration for you.\n\n"
        "🔹 Want to *stop* all ongoing actions? Just type:\n"
        "`stop all`\n\n"
        "🔐 *Important:* Only authorized users can use this bot in private chat. 😎\n\n"
        "🤖 _This bot was made by Ibr._"
    )
    bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ['Manual Mode', 'Auto Mode'])
def set_mode(message):
    user_id = message.from_user.id
    if message.text == 'Manual Mode':
        user_modes[user_id] = 'manual'
        bot.reply_to(message, 'You are now in *Manual Mode*.\nPlease provide `<ip> <port> <duration>`.', parse_mode='Markdown')
    elif message.text == 'Auto Mode':
        user_modes[user_id] = 'auto'
        bot.reply_to(message, 'You are now in *Auto Mode*.\nPlease provide `<ip> <port>`, and I\'ll choose the duration for you.', parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_type = message.chat.type
    
    if chat_type == 'private' and user_id not in AUTHORIZED_USERS:
        bot.reply_to(message, '⛔ *You are not authorized to use this bot.* Please contact the admin if you believe this is an error. 🤔\n\n_This bot was made by Ibr._', parse_mode='Markdown')
        return

    text = message.text.strip().lower()

    if text == 'stop all':
        stop_all_actions(message)
        return

    user_mode = user_modes.get(user_id, 'manual')  # Default to 'manual' if mode not set

    if user_mode == 'auto':
        # In auto mode, expect only IP and port
        match = re.match(r"(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\s(\d{1,5})", text)
        if match:
            ip, port = match.groups()
            duration = random.randint(80, 120)

            if not is_valid_ip(ip):
                bot.reply_to(message, "❌ *Invalid IP address!* Please provide a valid IP.\n\n_This bot was made by Ibr._", parse_mode='Markdown')
                return
            if not is_valid_port(port):
                bot.reply_to(message, "❌ *Invalid Port!* Port must be between 1 and 65535.\n\n_This bot was made by Ibr._", parse_mode='Markdown')
                return

            bot.reply_to(message, (
                f"🔧 *Got it! Starting action in Auto Mode...* 💥\n\n"
                f"🌍 *Target IP:* `{ip}`\n"
                f"🔌 *Port:* `{port}`\n"
                f"⏳ *Duration:* `{duration} seconds`\n\n"
                "Hang tight, action is being processed... ⚙️\n\n"
                "_This bot was made by Ibr._"
            ), parse_mode='Markdown')
            run_action(user_id, message, ip, port, duration)
        else:
            bot.reply_to(message, "⚠️ *Oops!* Please provide the IP and port in the correct format: `<ip> <port>`.\n\n_This bot was made by Ibr._", parse_mode='Markdown')

    elif user_mode == 'manual':
        # In manual mode, expect IP, port, and duration
        match = pattern.match(text)
        if match:
            ip, port, duration = match.groups()

            if not is_valid_ip(ip):
                bot.reply_to(message, "❌ *Invalid IP address!* Please provide a valid IP.\n\n_This bot was made by Ibr._", parse_mode='Markdown')
                return
            if not is_valid_port(port):
                bot.reply_to(message, "❌ *Invalid Port!* Port must be between 1 and 65535.\n\n_This bot was made by Ibr._", parse_mode='Markdown')
                return
            if not is_valid_duration(duration):
                bot.reply_to(message, "❌ *Invalid Duration!* The duration must be between 1 and 600 seconds.\n\n_This bot was made by Ibr._", parse_mode='Markdown')
                return

            bot.reply_to(message, (
                f"🔧 *Got it! Starting action in Manual Mode...* 💥\n\n"
                f"🌍 *Target IP:* `{ip}`\n"
                f"🔌 *Port:* `{port}`\n"
                f"⏳ *Duration:* `{duration} seconds`\n\n"
                "Hang tight, action is being processed... ⚙️\n\n"
                "_This bot was made by Ibr._"
            ), parse_mode='Markdown')
            run_action(user_id, message, ip, port, duration)
        else:
            bot.reply_to(message, (
                "⚠️ *Oops!* The format looks incorrect. Let's try again:\n"
                "`<ip> <port> <duration>`\n\n"
                "For example, type `192.168.1.100 8080 60` to run an action for 60 seconds.\n\n"
                "_This bot was made by Ibr._"
            ), parse_mode='Markdown')

def run_action(user_id, message, ip, port, duration):
    # Log the action
    logging.info(f"User {user_id} started action on IP {ip}, Port {port}, Duration {duration}s")

    # Run the action command
    full_command = f"./bgmi {ip} {port} {duration} 600"
    process = subprocess.Popen(full_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    processes[process.pid] = process

    # Schedule a timer to check process status after duration
    timer = Timer(int(duration), check_process_status, [message, process, ip, port, duration])
    timer.start()

def check_process_status(message, process, ip, port, duration):
    return_code = process.poll()
    if return_code is None:
        process.terminate()
        process.wait()
    
    processes.pop(process.pid, None)

    bot.reply_to(message, (
        f"✅ *Action completed successfully!* 🎉\n\n"
        f"🌐 *Target IP:* `{ip}`\n"
        f"🔌 *Port:* `{port}`\n"
        f"⏱ *Duration:* `{duration} seconds`\n\n"
        "💡 *Need more help?* Just send me another request, I'm here to assist! 🤗\n\n"
        "_This bot was made by Ibr._"
    ), parse_mode='Markdown')

def stop_all_actions(message):
    if processes:
        for pid, process in list(processes.items()):
            process.terminate()
            process.wait()
            processes.pop(pid, None)
        bot.reply_to(message, '🛑 *All actions have been stopped.* 😎\n\nFeel free to start a new action anytime! 🚀\n\n_This bot was made by Ibr._', parse_mode='Markdown')
    else:
        bot.reply_to(message, '🔕 *No actions are currently running.* 😴\n\n_This bot was made by Ibr._', parse_mode='Markdown')

# Start polling Made by IBR
bot.polling()
