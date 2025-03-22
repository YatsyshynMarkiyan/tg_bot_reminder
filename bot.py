import sqlite3
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Your Telegram bot token
TOKEN = os.getenv("API_TOKEN")

# Database setup
conn = sqlite3.connect('reminders.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    text TEXT,
    time INTEGER
)
''')
conn.commit()

# Define a router
router = Router()

# Helper function to generate the main menu
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Set Reminder", callback_data="set_reminder")],
        [InlineKeyboardButton(text="📋 List Reminders", callback_data="list_reminders")],
        [InlineKeyboardButton(text="❌ Delete Reminder", callback_data="delete_reminder")],
        [InlineKeyboardButton(text="🧹 Clear Chat", callback_data="clear_chat")]
    ])
    return keyboard

# /start command
@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "👋 Welcome to Reminder Bot!\n\n"
        "This bot helps you manage reminders effortlessly. Use the buttons below to navigate the bot's features.",
        reply_markup=get_main_menu()
    )

# Handle callback queries
@router.callback_query()
async def handle_callbacks(callback: CallbackQuery):
    if callback.data == "set_reminder":
        await callback.message.answer("Use the command: /set_reminder <minutes> <text>")
    elif callback.data == "list_reminders":
        await list_reminders(callback.message)
    elif callback.data == "delete_reminder":
        await callback.message.answer("Use the command: /delete_reminder <index>")
    elif callback.data == "clear_chat":
        await clear_chat(callback.message)
    else:
        await callback.message.answer("Unknown action. Please try again.")

# /set_reminder command - Adds a reminder for the user
@router.message(Command("set_reminder"))
async def set_reminder(message: Message):
    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer("Usage: /set_reminder <minutes> <text>")
            return

        time = int(args[1])
        if time <= 0:
            await message.answer("Time must be a positive integer.")
            return

        text = args[2].strip()
        if not text:
            await message.answer("Reminder text cannot be empty.")
            return

        cursor.execute(
            "INSERT INTO reminders (user_id, text, time) VALUES (?, ?, ?)",
            (message.from_user.id, text, time)
        )
        conn.commit()

        reminder_id = cursor.lastrowid
        await message.answer(f"Reminder set: '{text}' in {time} minutes.")

        await asyncio.sleep(time * 60)

        cursor.execute("SELECT id FROM reminders WHERE id = ?", (reminder_id,))
        if cursor.fetchone():
            await message.answer(f"⏰ Reminder: {text}")
            cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
    except Exception as e:
        await message.answer(f"An error occurred while setting the reminder: {str(e)}")

    pass

# /list_reminders command - Lists all active reminders for the user
@router.message(Command("list_reminders"))
async def list_reminders(message: Message):
    cursor.execute("SELECT text, time FROM reminders WHERE user_id = ?", (message.from_user.id,))
    reminders = cursor.fetchall()
    if not reminders:
        await message.answer("You have no reminders.")
    else:
        response = "Your reminders:\n"
        for idx, reminder in enumerate(reminders, start=1):
            response += f"{idx}. {reminder[0]} - in {reminder[1]} minutes\n"
        await message.answer(response)
    pass

# /delete_reminder command - Deletes a reminder by its index in the list
@router.message(Command("delete_reminder"))
async def delete_reminder(message: Message):
    try:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Usage: /delete_reminder <index>")
            return

        index = int(args[1])
        if index <= 0:
            await message.answer("Index must be a positive integer.")
            return

        cursor.execute("SELECT id FROM reminders WHERE user_id = ?", (message.from_user.id,))
        reminders = cursor.fetchall()

        if index > len(reminders):
            await message.answer("Invalid index. Please provide a valid reminder index.")
            return

        reminder_id = reminders[index - 1][0]
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()

        await message.answer(f"Reminder {index} deleted.")
    except ValueError:
        await message.answer("Please specify a valid index.")
    pass

# /clear_chat command
@router.message(Command("clear_chat"))
async def clear_chat(message: Message, bot: Bot):
    try:
        # Get the ID of the last message
        last_message_id = message.message_id

        # Delete all messages from the bot and the user
        for message_id in range(last_message_id, 0, -1):
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=message_id)
            except Exception as e:
                # Ignore errors, for example, if the message is not found or is too old
                print(f"Could not delete message {message_id}: {e}")
                
        # Confirmation of chat clearing
        await message.answer("Chat cleared!")
    except Exception as e:
        # Handle unexpected errors
        await message.answer(f"An error occurred while clearing the chat: {str(e)}")


@router.message(Command("check_permissions"))
async def check_permissions(message: Message, bot: Bot):
    chat = await bot.get_chat(message.chat.id)
    bot_member = await bot.get_chat_member(chat.id, bot.id)

    if bot_member.is_chat_admin():
        permissions = bot_member['privileges']
        await message.answer(f"Bot has the following permissions:\n{permissions}")
    else:
        await message.answer("Bot is not an admin in this chat.")

# Function to set commands for the bot's menu
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="set_reminder", description="Set a new reminder"),
        BotCommand(command="list_reminders", description="View all reminders"),
        BotCommand(command="delete_reminder", description="Delete a reminder"),
        BotCommand(command="clear_chat", description="Clear chat history")
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Set bot commands
    await set_bot_commands(bot)

    try:
        print("Bot is running...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        print("Bot is shutting down...")
    finally:
        await bot.session.close()
        print("Bot stopped.")

if __name__ == '__main__':
    asyncio.run(main())
