import os
import emoji
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import create_config
from utils import *


# Load env variables
load_dotenv()

# Get env names
USER_ID = os.getenv("USER_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configure logging
logging.basicConfig(level=logging.INFO)


# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


async def send_signal(bot: Bot):
    # Get config
    config = create_config()

    # Calculate signal
    data = get_signal(config)
    data = data[:-1].copy()  # drop the last uncompleted row

    # Send info if the signal is generated
    row = data.iloc[-1]
    if row.hard_to_grow or row.hard_to_fall:
        if row.hard_to_grow:
            text_report = (
                emoji.emojize(":red_circle:") + "Hard to grow: " + str(row.vpr)
            )

        if row.hard_to_fall:
            text_report = (
                emoji.emojize(":green_circle:") + "Hard to fall: " + str(row.vpr)
            )

        # Generate plot
        fig = create_plot(config, data)

        await bot.send_photo(USER_ID, fig, caption=text_report)


@dp.message_handler(commands=["signal"])
async def send_info(message: types.Message):
    # Get config
    config = create_config()

    # Calculate signal
    data = get_signal(config)
    data = data[:-1].copy()  # drop the last uncompleted row

    # Generate plot
    fig = create_plot(config, data)

    text = "VPR: " + str(data.iloc[-1].vpr)

    await message.answer_photo(fig, caption=text)


@dp.message_handler(commands=["start", "help"])
async def send_welcome(message: types.Message):
    await message.answer("Hi!")


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)


if __name__ == "__main__":
    # Sends every minute pass 5 seconds
    now = datetime.now()
    datetime_now = datetime(
        year=now.year, month=now.month, day=now.day, hour=now.hour, second=5
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_signal,
        trigger="interval",
        start_date=datetime_now,
        minutes=60,
        seconds=5,
        kwargs={"bot": bot},
    )
    scheduler.start()

    executor.start_polling(dp, skip_updates=True)
