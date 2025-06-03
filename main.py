from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
import requests
import m3u8
import json
import subprocess
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait
from p_bar import progress_bar
from subprocess import getstatusoutput
from aiohttp import ClientSession
import helper
from logger import logging
import time
import asyncio
from pyrogram.types import User, Message, enums
import sys
import re
import os
import urllib
import urllib.parse
import tgcrypto
import cloudscraper
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64encode, b64decode
from helper import *
import aiohttp
import aiofiles
import zipfile
import shutil
import ffmpeg

from config import API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL, BIN_CHANNEL

# Global dictionary to track user tasks
user_tasks = {}

cyt = "https://graph.org/file/996d4fc24564509244988-a7d93d020c96973ba8.jpg"
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
token_cp = "eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9gft"

# Define the owner's user ID
OWNER_ID = 6400973182
SUDO_USERS = [6400973182]
AUTH_CHANNEL = -1002595188554

def is_authorized(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS

# Initialize bot
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Message queue for user inputs
message_queues = {}

async def wait_for_message(chat_id: int, timeout: int = 300) -> Message:
    queue = asyncio.Queue()
    message_queues[chat_id] = queue
    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        if chat_id in message_queues:
            del message_queues[chat_id]

@bot.on_message(filters.all, group=-1)
async def message_waiter(_, msg: Message):
    chat_id = msg.chat.id
    if chat_id in message_queues:
        await message_queues[chat_id].put(msg)

async def show_random_emojis(msg: Message):
    emojis = [
        "🎊", "🔮", "😎", "⚡️", "🚀", "✨", "💥", "🎉", "🥂", "🍾", 
        "🦠", "🤖", "❤️‍🔥", "🕊️", "💃", "🥳", "🐅", "🦁",
    ]
    emoji_message = await msg.reply_text(" ".join(random.choices(emojis, k=1)))
    return emoji_message

# Stop command handler - stops current user's operations
@bot.on_message(filters.command("stop"))
async def stop_handler(_, msg: Message):
    user_id = msg.from_user.id
    # Create user-specific directory path
    user_dir = f"./downloads/{user_id}"
    
    # Cancel any ongoing tasks for this user
    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        del user_tasks[user_id]
        await msg.reply_text("⏹️ **Your operations have been stopped**")
    else:
        await msg.reply_text("ℹ️ **No active operations to stop**")
    
    # Clean up user's downloaded files
    if os.path.exists(user_dir):
        try:
            shutil.rmtree(user_dir)
            await msg.reply_text("🧹 **Your downloaded files have been cleaned**")
        except Exception as e:
            logging.error(f"Error cleaning files for user {user_id}: {str(e)}")
            await msg.reply_text("⚠️ **Error cleaning files, but operations stopped**")
    else:
        await msg.reply_text("ℹ️ **No downloaded files to clean**")


# Restart command handler - full bot restart (owner only)
@bot.on_message(filters.command("restart"))
async def restart_handler(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        await msg.reply_text("**🚫 You are not authorized to use this command.**")
        return
    
    # Cancel all ongoing tasks
    for task in user_tasks.values():
        task.cancel()
    
    # Clean all downloads
    if os.path.exists("./downloads"):
        try:
            shutil.rmtree("./downloads")
        except Exception as e:
            logging.error(f"Error cleaning all downloads: {str(e)}")
    
    await msg.reply_text("🔄 **Restarting bot...**")
    os.execl(sys.executable, sys.executable, *sys.argv)

# Sudo command to add/remove sudo users
@bot.on_message(filters.command("sudo"))
async def sudo_command(bot: Client, message: Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        await msg.reply_text("**🚫 You are not authorized to use this command.**")
        return

    try:
        args = message.text.split(" ", 2)
        if len(args) < 2:
            await message.reply_text(
                "**Usage:** `/sudo add <user_id>` or `/sudo remove <user_id>`"
            )
            return

        action = args[1].lower()
        target_user_id = int(args[2])

        if action == "add":
            if target_user_id not in SUDO_USERS:
                SUDO_USERS.append(target_user_id)
                await message.reply_text(
                    f"**✅ User {target_user_id} added to sudo list.**"
                )
            else:
                await message.reply_text(
                    f"**⚠️ User {target_user_id} is already in the sudo list.**"
                )
        elif action == "remove":
            if target_user_id == OWNER_ID:
                await message.reply_text(
                    "**🚫 The owner cannot be removed from the sudo list.**"
                )
            elif target_user_id in SUDO_USERS:
                SUDO_USERS.remove(target_user_id)
                await message.reply_text(
                    f"**✅ User {target_user_id} removed from sudo list.**"
                )
            else:
                await message.reply_text(
                    f"**⚠️ User {target_user_id} is not in the sudo list.**"
                )
        else:
            await message.reply_text(
                "**Usage:** `/sudo add <user_id>` or `/sudo remove <user_id>`"
            )
    except Exception as e:
        await message.reply_text(f"**Error:** {str(e)}")

@bot.on_message(filters.command("start"))
async def start_command(bot: Client, msg: Message):
    start_message = f"""
> Hᴇʟʟᴏ  [{msg.from_user.first_name}](tg://user?id={msg.from_user.id})

**Wᴇʟᴄᴏᴍᴇ ᴛᴏ Tᴇxᴛ Uᴘʟᴏᴀᴅᴇʀ Bᴏᴛ 🤖**✨

➤ --ᴛᴏ Uᴘʟᴏᴅ α ᴛxᴛ ғɪʟᴇ:--
  • sᴇɴᴅ /txt  
  • ᴛʜᴇɴ sᴇɴᴅ ʏᴏᴜʀ ᴛxᴛ ғɪʟᴇ.
➤ --ᴛᴏ sᴛᴏᴘ ᴜᴘʟᴏᴀᴅɪɴɢ:-- 
  • sᴇɴᴅ /stop

🚀 Exᴘᴇʀɪᴇɴᴄᴇ Lɪɢʜᴛɴɪɴɢ-ғᴀsᴛ Tᴇxᴛ Uᴘʟᴏᴀᴅs!
"""
    await msg.reply_text(
        start_message,
        disable_web_page_preview=True,
        protect_content=True
    )

# List users command
@bot.on_message(filters.command("userlist") & filters.user(SUDO_USERS))
async def list_users(client: Client, msg: Message):
    if SUDO_USERS:
        users_list = "\n".join([f"User ID : `{user_id}`" for user_id in SUDO_USERS])
        await msg.reply_text(f"SUDO_USERS :\n{users_list}")
    else:
        await msg.reply_text("No sudo users.")

# Help command
@bot.on_message(filters.command("help"))
async def help_command(client: Client, msg: Message):
    help_text = (
        "`/start` - Start the bot⚡\n\n"
        "`/tushar` or `/upload` - Download and upload files (sudo)🎬\n\n"
        "`/restart` - Restart the bot🔮\n\n"
        "`/stop` - Stop ongoing process🛑\n\n"
        "`/sudo add` - Add user or group or channel (owner)🎊\n\n"
        "`/sudo remove` - Remove user or group or channel (owner)❌\n\n"
        "`/userlist` - List of sudo user or group or channel📜\n\n"
    )
    await msg.reply_text(help_text)

@bot.on_message(filters.command("txt"))
async def upload(bot: Client, msg: Message):
    user_id = msg.from_user.id
    # Create user-specific directory
    user_dir = f"./downloads/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    # Store the task for potential cancellation
    task = asyncio.current_task()
    user_tasks[user_id] = task
    
    try:
        editable = await msg.reply_text(f"⚡𝗦𝗘𝗡𝗗 𝗧𝗫𝗧 𝗙𝗜𝗟𝗘⚡")
        input_msg = await wait_for_message(msg.chat.id)
        if not input_msg or not input_msg.document:
            await editable.edit("**🚫 No file received. Process cancelled.**")
            return
        
        # Download to user-specific directory
        y = await input_msg.download(file_name=os.path.join(user_dir, os.path.basename(input_msg.document.file_name)))
        await input_msg.delete()
        file_name, ext = os.path.splitext(os.path.basename(y))
        
        # Log TXT file to log channel
        user_info = f"👤 User ID: `{user_id}`\n"
        if msg.from_user.username:
            user_info += f"👤 Username: @{msg.from_user.username}\n"
        if msg.chat.id != user_id:  # If in group
            user_info += f"💬 Chat ID: `{msg.chat.id}`\n"
        
        try:
            await bot.send_document(
                chat_id=LOG_CHANNEL,
                document=y,
                caption=f"📝 New TXT file received\n{user_info}"
            )
        except Exception as e:
            logging.error(f"Failed to log TXT file: {str(e)}")
        
        if file_name.endswith("_helper"):
            y = helper.decrypt_file_txt(y)
        else:
            x = y
        
        pdf_count = 0
        img_count = 0
        zip_count = 0
        video_count = 0
        
        try:
            with open(x, "r") as f:
                content = f.read()
            content = content.split("\n")
            
            links = []
            for i in content:
                if "://" in i:
                    url = i.split("://", 1)[1]
                    links.append(i.split("://", 1))
                    if ".pdf" in url:
                        pdf_count += 1
                    elif url.endswith((".png", ".jpeg", ".jpg")):
                        img_count += 1
                    elif ".zip" in url:
                        zip_count += 1
                    else:
                        video_count += 1
            os.remove(x)
        except:
            await msg.reply_text("😶𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗙𝗶𝗹𝗲 𝗜𝗻𝗽𝘂𝘁😶")
            os.remove(x)
            return
        
        await editable.edit(f"`𝗧𝗼𝘁𝗮𝗹 🔗 𝗟𝗶𝗻𝗸𝘀 𝗙𝗼𝘂𝗻𝗱 𝗔𝗿𝗲 {len(links)}\n\n🔹Img : {img_count}  🔹Pdf : {pdf_count}\n🔹Zip : {zip_count}  🔹Video : {video_count}\n\n𝗦𝗲𝗻𝗱 𝗙𝗿𝗼𝗺 𝗪𝗵𝗲𝗿𝗲 𝗬𝗼𝘂 𝗪𝗮𝗻𝘁 𝗧𝗼 𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱.`")
        
        input0 = await wait_for_message(msg.chat.id)
        if not input0:
            await editable.edit("**🚫 No input received. Process cancelled.**")
            return
        raw_text = input0.text
        await input0.delete()
        try:
            arg = int(raw_text)
        except:
            arg = 1
        
        await editable.edit("📚 𝗘𝗻𝘁𝗲𝗿 𝗬𝗼𝘂𝗿 𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 📚\n\n🦠 𝗦𝗲𝗻𝗱 `1` 𝗙𝗼𝗿 𝗨𝘀𝗲 𝗗𝗲𝗳𝗮𝘂𝗹𝘁 🦠")
        input1 = await wait_for_message(msg.chat.id)
        if not input1:
            await editable.edit("**🚫 No input received. Process cancelled.**")
            return
        raw_text0 = input1.text
        await input1.delete()
        if raw_text0 == "1":
            b_name = file_name
        else:
            b_name = raw_text0
        
        await editable.edit("**📸 𝗘𝗻𝘁𝗲𝗿 𝗥𝗲𝘀𝗼𝗹𝘂𝘁𝗶𝗼𝗻 📸**\n➤ `144`\n➤ `240`\n➤ `360`\n➤ `480`\n➤ `720`\n➤ `1080`")
        input2 = await wait_for_message(msg.chat.id)
        if not input2:
            await editable.edit("**🚫 No input received. Process cancelled.**")
            return
        raw_text2 = input2.text
        await input2.delete()
        try:
            if raw_text2 == "144":
                res = "256x144"
            elif raw_text2 == "240":
                res = "426x240"
            elif raw_text2 == "360":
                res = "640x360"
            elif raw_text2 == "480":
                res = "854x480"
            elif raw_text2 == "720":
                res = "1280x720"
            elif raw_text2 == "1080":
                res = "1920x1080"
            else:
                res = "UN"
        except Exception:
            res = "UN"
        
        await editable.edit("📛 𝗘𝗻𝘁𝗲𝗿 𝗬𝗼𝘂𝗿 𝗡𝗮𝗺𝗲 📛\n\n🐥 𝗦𝗲𝗻𝗱 `1` 𝗙𝗼𝗿 𝗨𝘀𝗲 𝗗𝗲𝗳𝗮𝘂𝗹𝘁 🐥")
        input3 = await wait_for_message(msg.chat.id)
        if not input3:
            await editable.edit("**🚫 No input received. Process cancelled.**")
            return
        raw_text3 = input3.text
        await input3.delete()
        credit = "️[𝗧𝘂𝘀𝗵𝗮𝗿](https://t.me/newstudent1885)"
        if raw_text3 == "1":
            CR = "[𝗧𝘂𝘀𝗵𝗮𝗿](https://t.me/newstudent1885)"
        elif raw_text3:
            try:
                text, link = raw_text3.split(",")
                CR = f"[{text.strip()}]({link.strip()})"
            except ValueError:
                CR = raw_text3
        else:
            CR = credit
        
        await editable.edit("**𝗘𝗻𝘁𝗲𝗿 𝗣𝘄 𝗧𝗼𝗸𝗲𝗻 𝗙𝗼𝗿 𝗣𝘄 𝗨𝗽𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗼𝗿 𝗦𝗲𝗻𝗱 `3` 𝗙𝗼𝗿 𝗢𝘁𝗵𝗲𝗿𝘀**")
        input4 = await wait_for_message(msg.chat.id)
        if not input4:
            await editable.edit("**🚫 No input received. Process cancelled.**")
            return
        raw_text4 = input4.text
        await input4.delete()
        if raw_text4 == "3":
            MR = token_cp
        else:
            MR = raw_text4
        
        await editable.edit("𝗡𝗼𝘄 𝗦𝗲𝗻𝗱 𝗧𝗵𝗲 𝗧𝗵𝘂𝗺𝗯 𝗨𝗿𝗹 𝗘𝗴 » https://graph.org/file/13a89d77002442255efad-989ac290c1b3f13b44.jpg\n\n𝗢𝗿 𝗜𝗳 𝗗𝗼𝗻'𝘁 𝗪𝗮𝗻𝘁 𝗧𝗵𝘂𝗺𝗯𝗻𝗮𝗶𝗹 𝗦𝗲𝗻𝗱 = 𝗻𝗼")
        input6 = await wait_for_message(msg.chat.id)
        if not input6:
            await editable.edit("**🚫 No input received. Process cancelled.**")
            return
        raw_text6 = input6.text
        await input6.delete()
        await editable.delete()
        
        thumb = raw_text6
        if thumb.startswith("http://") or thumb.startswith("https://"):
            async with aiohttp.ClientSession() as session:
                async with session.get(thumb) as resp:
                    if resp.status == 200:
                        thumb_path = os.path.join(user_dir, 'thumb.jpg')
                        async with aiofiles.open(thumb_path, 'wb') as f:
                            await f.write(await resp.read())
                        thumb = thumb_path
                    else:
                        thumb = "no"
        else:
            thumb = "no"
        failed_count = 0
        if len(links) == 1:
            count = 1
        else:
            count = int(raw_text)

        try:
            for i in range(count - 1, len(links)):
                # Check if task was cancelled
                if user_id in user_tasks and user_tasks[user_id].cancelled():
                    await msg.reply_text("🛑 **Operation cancelled by user request**")
                    return

            V = (
                links[i][1]
                .replace("file/d/", "uc?export=download&id=")
                .replace("www.youtube-nocookie.com/embed", "youtu.be")
                .replace("?modestbranding=1", "")
                .replace("/view?usp=sharing", "")
            )  # .replace("mpd","m3u8")
            url = "https://" + V

            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(
                        url,
                        headers={
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                            "Accept-Language": "en-US,en;q=0.9",
                            "Cache-Control": "no-cache",
                            "Connection": "keep-alive",
                            "Pragma": "no-cache",
                            "Referer": "http://www.visionias.in/",
                            "Sec-Fetch-Dest": "iframe",
                            "Sec-Fetch-Mode": "navigate",
                            "Sec-Fetch-Site": "cross-site",
                            "Upgrade-Insecure-Requests": "1",
                            "User-Agent": "Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36",
                            "sec-ch-ua": '"Chromium";v="107", "Not=A?Brand";v="24"',
                            "sec-ch-ua-mobile": "?1",
                            "sec-ch-ua-platform": '"Android"',
                        },
                    ) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(
                            1
                        )
            elif "https://cpvod.testbook.com/" in url:
                url = url.replace(
                    "https://cpvod.testbook.com/",
                    "https://media-cdn.classplusapp.com/drm/",
                )
                url = "https://dragoapi.vercel.app/classplus?link=" + url
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
                url = f"https://anonymousrajputplayer-9ab2f2730a02.herokuapp.com/pw?url={url}&token={raw_text4}"

            elif "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'

            elif "edge.api.brightcove.com" in url:
                bcov = "bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg"
                url = url.split("bcov_auth")[0] + bcov

            elif "classplusapp.com/drm/" in url:
                url = "https://dragoapi.vercel.app/classplus?link=" + url
                mpd, keys = helper.get_mps_and_keys(url)
                url = mpd
                keys_string = " ".join([f"--key {key}" for key in keys])

            elif "videos.classplusapp" in url:
                url = requests.get(
                    f"https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}",
                    headers={
                        "x-access-token": "eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9"
                    },
                ).json()["url"]

            elif (
                "tencdn.classplusapp" in url
                or "media-cdn-alisg.classplusapp.com" in url
                or "videos.classplusapp" in url
                or "media-cdn.classplusapp" in url
            ):
                headers = {
                    "Host": "api.classplusapp.com",
                    "x-access-token": "eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ0lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9",
                    "user-agent": "Mobile-Android",
                    "app-version": "1.4.37.1",
                    "api-version": "18",
                    "device-id": "5d0d17ac8b3c9f51",
                    "device-details": "2848b866799971ca_2848b8667a33216c_SDK-30",
                    "accept-encoding": "gzip",
                }
                params = (("url", f"{url}"),)
                response = requests.get(
                    "https://api.classplusapp.com/cams/uploader/video/jw-signed-url",
                    headers=headers,
                    params=params,
                )
                url = response.json()["url"]

            elif "edge.api.brightcove.com" in url:
                bcov = "bcov_auth=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3MjQyMzg3OTEsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiZEUxbmNuZFBNblJqVEROVmFWTlFWbXhRTkhoS2R6MDkiLCJmaXJzdF9uYW1lIjoiYVcxV05ITjVSemR6Vm10ak1WUlBSRkF5ZVNzM1VUMDkiLCJlbWFpbCI6Ik5Ga3hNVWhxUXpRNFJ6VlhiR0ppWTJoUk0wMVdNR0pVTlU5clJXSkRWbXRMTTBSU2FHRnhURTFTUlQwPSIsInBob25lIjoiVUhVMFZrOWFTbmQ1ZVcwd1pqUTViRzVSYVc5aGR6MDkiLCJhdmF0YXIiOiJLM1ZzY1M4elMwcDBRbmxrYms4M1JEbHZla05pVVQwOSIsInJlZmVycmFsX2NvZGUiOiJOalZFYzBkM1IyNTBSM3B3VUZWbVRtbHFRVXAwVVQwOSIsImRldmljZV90eXBlIjoiYW5kcm9pZCIsImRldmljZV92ZXJzaW9uIjoiUShBbmRyb2lkIDEwLjApIiwiZGV2aWNlX21vZGVsIjoiU2Ftc3VuZyBTTS1TOTE4QiIsInJlbW90ZV9hZGRyIjoiNTQuMjI2LjI1NS4xNjMsIDU0LjIyNi4yNTUuMTYzIn19.snDdd-PbaoC42OUhn5SJaEGxq0VzfdzO49WTmYgTx8ra_Lz66GySZykpd2SxIZCnrKR6-R10F5sUSrKATv1CDk9ruj_ltCjEkcRq8mAqAytDcEBp72-W0Z7DtGi8LdnY7Vd9Kpaf499P-y3-godolS_7ixClcYOnWxe2nSVD5C9c5HkyisrHTvf6NFAuQC_FD3TzByldbPVKK0ag1UnHRavX8MtttjshnRhv5gJs5DQWj4Ir_dkMcJ4JaVZO3z8j0OxVLjnmuaRBujT-1pavsr1CCzjTbAcBvdjUfvzEhObWfA1-Vl5Y4bUgRHhl1U-0hne4-5fF0aouyu71Y6W0eg"
                url = url.split("bcov_auth")[0] + bcov

            elif "encrypted.m" in url:
                appxkey = url.split("*")[1]
                url = url.split("*")[0]

            elif "allenplus" in url or "player.vimeo" in url:
                if "controller/videoplay" in url:
                    url0 = (
                        "https://player.vimeo.com/video/"
                        + url.split("videocode=")[1].split("&videohash=")[0]
                    )
                    url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url0}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
                else:
                    url = f"https://master-api-v3.vercel.app/allenplus-vimeo?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"

            elif url.startswith("https://videotest.adda247.com/"):
                if url.split("/")[3] != "demo":
                    url = f'https://videotest.adda247.com/demo/{url.split("https://videotest.adda247.com/")[1]}'

            elif "master.mpd" in url:
                # vid_id =  url.split('/')[-2]
                url = f"{api_url}pw-dl?url={url}&token={token}&authorization={api_token}&q={raw_text2}"

            name1 = (
                links[i][0]
                .replace("\t", "")
                .replace(":", "")
                .replace("/", "")
                .replace("+", "")
                .replace("#", "")
                .replace("|", "")
                .replace("@", "")
                .replace("*", "")
                .replace(".", "")
                .replace("https", "")
                .replace("http", "")
                .strip()
            )
            name = f"{name1[:60]} "

            if "youtu" in url:
                ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
            else:
                ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

            if "jw-prod" in url:
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

            try:
                cc = f"**[🎬] 𝗩𝗶𝗱_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.({res}).𝔗𝔲𝔰𝔥𝔞𝔯.mkv\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**"
                # cpw = f'**[🎬] 𝗩𝗶𝗱_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.({res}).𝔗𝔲𝔰𝔥𝔞𝔯.mkv\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**'
                cyt = f'**[🎬] 𝗩𝗶𝗱_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.({res}).𝔗𝔲𝔰𝔥𝔞𝔯.mp4\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**'
                cpvod = f'**[🎬] 𝗩𝗶𝗱_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.({res}).𝔗𝔲𝔰𝔥𝔞𝔯.mkv\n\n\n🔗𝗩𝗶𝗱𝗲𝗼 𝗨𝗿𝗹 ➤ <a href="{url}">__Click Here to Watch Video__</a>\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**'
                cimg = f"**[📁] 𝗜𝗺𝗴_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.𝔗𝔲𝔰𝔥𝔞𝔯.jpg\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**"
                cczip = f"**[📁] 𝗣𝗱𝗳_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.𝔗𝔲𝔰𝔥𝔞𝔯.zip\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**"
                cc1 = f"**[📁] 𝗣𝗱𝗳_𝗜𝗱 : {str(count).zfill(3)}.\n\n\n☘️𝗧𝗶𝘁𝗹𝗲 𝗡𝗮𝗺𝗲 ➤ {name1}.𝔗𝔲𝔰𝔥𝔞𝔯.pdf\n\n\n<pre><code>📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 ➤ {b_name}</code></pre>\n\n\n📥 𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤  {CR}**"

                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(
                            chat_id=m.chat.id, document=ka, caption=cc1
                        )
                        count += 1
                        os.remove(ka)
                        time.sleep(1)
                    except FloodWait as e:
                        await msg.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".zip" in url:
                    try:
                        cmd = f'yt-dlp -o "{name}.zip" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_document(
                            chat_id=m.chat.id, document=f"{name}.zip", caption=cczip
                        )
                        count += 1
                        os.remove(f"{name}.zip")
                    except FloodWait as e:
                        await msg.reply_text(str(e))
                        time.sleep(e.x)
                        count += 1
                        pass

                elif "pdf*" in url:
                    pdf_key = url.split("*")[1]
                    url = url.split("*")[0]
                    pdf_enc = await helper.download_and_decrypt_pdf(url, name, pdf_key)
                    copy = await bot.send_document(
                        chat_id=m.chat.id, document=pdf_enc, caption=cc1
                    )
                    count += 1
                    os.remove(pdf_enc)
                    continue

                elif ".pdf" in url:
                    try:
                        await asyncio.sleep(4)
                        # Replace spaces with %20 in the URL
                        url = url.replace(" ", "%20")

                        # Create a cloudscraper session
                        scraper = cloudscraper.create_scraper()

                        # Send a GET request to download the PDF
                        response = scraper.get(url)

                        # Check if the response status is OK
                        if response.status_code == 200:
                            # Write the PDF content to a file
                            with open(f"{name}.pdf", "wb") as file:
                                file.write(response.content)

                            # Send the PDF document
                            await asyncio.sleep(4)
                            copy = await bot.send_document(
                                chat_id=m.chat.id, document=f"{name}.pdf", caption=cc1
                            )
                            count += 1

                            # Remove the PDF file after sending
                            os.remove(f"{name}.pdf")
                        else:
                            await msg.reply_text(
                                f"Failed to download PDF: {response.status_code} {response.reason}"
                            )

                    except FloodWait as e:
                        await msg.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif ".pdf" in url:
                    try:
                        if (
                            "cwmediabkt99" in url
                        ):  # if cw urls pdf is found if error then contact me with error
                            time.sleep(2)
                            cmd = f'yt-dlp -o "{name}.pdf" "https://master-api-v3.vercel.app/cw-pdf?url={url}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            os.system(download_cmd)
                            copy = await bot.send_document(
                                chat_id=m.chat.id, document=f"{name}.pdf", caption=cc1
                            )
                            count += 1
                            os.remove(f"{name}.pdf")

                        else:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            # os.system(download_cmd)
                            # file_path= f'{name}.pdf'
                            # new_file_path = await helper.watermark_pdf(file_path, watermark_text)
                            # copy = await bot.send_document(chat_id=m.chat.id, document=new_file_path, caption=cc1)
                            os.system(download_cmd)
                            copy = await bot.send_document(
                                chat_id=m.chat.id, document=f"{name}.pdf", caption=cc1
                            )
                            count += 1
                            # os.remove(new_file_path)
                            os.remove(f"{name}.pdf")

                    except FloodWait as e:
                        await msg.reply_text(str(e))
                        time.sleep(e.x)
                        continue

                elif any(img in url.lower() for img in [".jpeg", ".png", ".jpg"]):
                    try:
                        subprocess.run(
                            ["wget", url, "-O", f"{name}.jpg"], check=True
                        )  # Fixing this line
                        await bot.send_photo(
                            chat_id=m.chat.id,
                            caption=cimg,
                            photo=f"{name}.jpg",
                        )
                        count += 1
                        await asyncio.sleep(1)
                        continue
                    except subprocess.CalledProcessError:
                        await msg.reply(
                            "Failed to download the image. Please check the URL."
                        )
                    except Exception as e:
                        await msg.reply(f"An error occurred: {e}")
                    finally:
                        # Clean up the downloaded file
                        if os.path.exists(f"{name}.jpg"):
                            os.remove(f"{name}.jpg")

                elif "youtu" in url:
                    try:
                        await bot.send_photo(
                            chat_id=m.chat.id, photo=photo, caption=cyt
                        )
                        count += 1
                    except Exception as e:
                        await msg.reply_text(str(e))
                        await asyncio.sleep(1)
                        continue

                elif ".ws" in url and url.endswith(".ws"):
                    try:
                        await helper.pdf_download(
                            f"{api_url}utkash-ws?url={url}&authorization={api_token}",
                            f"{name}.html",
                        )
                        time.sleep(1)
                        await bot.send_document(
                            chat_id=m.chat.id, document=f"{name}.html", caption=cc1
                        )
                        os.remove(f"{name}.html")
                        count += 1
                        time.sleep(5)
                    except FloodWait as e:
                        await asyncio.sleep(e.x)
                        await msg.reply_text(str(e))
                        continue

                elif "encrypted.m" in url:
                    emoji_message = await show_random_emojis(message)
                    remaining_links = len(links) - count
                    Show = f"**🍁 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗜𝗡𝗚 🍁**\n\n**📝ɴᴀᴍᴇ » ** `{name}\n\n🔗ᴛᴏᴛᴀʟ ᴜʀʟ » {len(links)}\n\n🗂️ɪɴᴅᴇx » {str(count)}/{len(links)}\n\n🌐ʀᴇᴍᴀɪɴɪɴɢ ᴜʀʟ » {remaining_links}\n\n❄ǫᴜᴀʟɪᴛʏ » {res}`\n\n**🔗ᴜʀʟ » ** `{url}`\n\n🤖𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 ➤ 𝗧𝗨𝗦𝗛𝗔𝗥\n\n🙂 चलो फिर से अजनबी बन जायें 🙂"
                    prog = await msg.reply_text(Show)
                    res_file = await helper.download_and_decrypt_video(
                        url, cmd, name, appxkey
                    )
                    filename = res_file

                    await prog.delete(True)
                    await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    await asyncio.sleep(1)
                    continue

                elif "drmcdni" in url or "drm/wv" in url:
                    emoji_message = await show_random_emojis(message)
                    remaining_links = len(links) - count
                    Show = f"**🍁 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗜𝗡𝗚 🍁**\n\n**📝ɴᴀᴍᴇ » ** `{name}\n\n🔗ᴛᴏᴛᴀʟ ᴜʀʟ » {len(links)}\n\n🗂️ɪɴᴅᴇx » {str(count)}/{len(links)}\n\n🌐ʀᴇᴍᴀɪɴɪɴɢ ᴜʀʟ » {remaining_links}\n\n❄ǫᴜᴀʟɪᴛʏ » {res}`\n\n**🔗ᴜʀʟ » ** `{url}`\n\n🤖𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 ➤ 𝗧𝗨𝗦𝗛𝗔𝗥\n\n🙂 चलो फिर से अजनबी बन जायें 🙂"
                    prog = await msg.reply_text(Show)
                    # Use the decrypt_and_merge_video function
                    res_file = await helper.decrypt_and_merge_video(
                        mpd, keys_string, path, name, raw_text2
                    )

                    filename = res_file
                    await prog.delete(True)
                    await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    await asyncio.sleep(1)
                    continue

                else:
                    emoji_message = await show_random_emojis(message)
                    remaining_links = len(links) - count
                    Show = f"**🍁 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗𝗜𝗡𝗚 🍁**\n\n**📝ɴᴀᴍᴇ » ** `{name}\n\n🔗ᴛᴏᴛᴀʟ ᴜʀʟ » {len(links)}\n\n🗂️ɪɴᴅᴇx » {str(count)}/{len(links)}\n\n🌐ʀᴇᴍᴀɪɴɪɴɢ ᴜʀʟ » {remaining_links}\n\n❄ǫᴜᴀʟɪᴛʏ » {res}`\n\n**🔗ᴜʀʟ » ** `{url}`\n\n🤖𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 ➤ 𝗧𝗨𝗦𝗛𝗔𝗥\n\n🙂 चलो फिर से अजनबी बन जायें 🙂"
                    prog = await msg.reply_text(Show)

                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await emoji_message.delete()
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
                    count += 1
                    time.sleep(1)

            except Exception as e:
                await msg.reply_text(
                    f"‼️𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱𝗶𝗻𝗴 𝗙𝗮𝗶𝗹𝗲𝗱‼️\n\n"
                    f"📝𝗡𝗮𝗺𝗲 » `{name}`\n\n"
                    f'🔗𝗨𝗿𝗹 » <a href="{url}">__**Click Here to See Link**__</a>`'
                )

                count += 1
                failed_count += 1
                continue

            except Exception as e:
                await msg.reply_text(e)
            await msg.reply_text(
        f"`✨𝗕𝗔𝗧𝗖𝗛 𝗦𝗨𝗠𝗠𝗔𝗥𝗬✨\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"📛𝗜𝗻𝗱𝗲𝘅 𝗥𝗮𝗻𝗴𝗲 » ({raw_text} to {len(links)})\n"
        f"📚𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 » {b_name}\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"✨𝗧𝗫𝗧 𝗦𝗨𝗠𝗠𝗔𝗥𝗬✨ : {len(links)}\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"🔹𝗩𝗶𝗱𝗲𝗼 » {video_count}\n🔹𝗣𝗱𝗳 » {pdf_count}\n🔹𝗜𝗺𝗴 » {img_count}\n🔹𝗭𝗶𝗽 » {zip_count}\n🔹𝗙𝗮𝗶𝗹𝗲𝗱 𝗨𝗿𝗹 » {failed_count}\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"✅𝗦𝗧𝗔𝗧𝗨𝗦 » 𝗖𝗢𝗠𝗣𝗟𝗘𝗧𝗘𝗗`"
    )
            await msg.reply_text(f"<pre><code>📥𝗘𝘅𝘁𝗿𝗮𝗰𝘁𝗲𝗱 𝗕𝘆 ➤『{CR}』</code></pre>")
            await msg.reply_text(f"<pre><code>『😏𝗥𝗲𝗮𝗰𝘁𝗶𝗼𝗻 𝗞𝗼𝗻 𝗗𝗲𝗴𝗮😏』</code></pre>")

        except asyncio.CancelledError:
            await msg.reply_text("⏹️ **Operation stopped by user request**")
        except Exception as e:
            await msg.reply_text(f"❌ **Unexpected error:** {str(e)}")
        finally:
        # Clean up task tracking
            if user_id in user_tasks:
                del user_tasks[user_id]

@bot.on_message(filters.all)
async def message_handler(_, msg: Message):
    chat_id = msg.chat.id
    if chat_id in message_queues:
        await message_queues[chat_id].put(msg)

if __name__ == "__main__":
    # Ensure downloads directory exists
    os.makedirs("./downloads", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Start the bot
    logging.info("Starting bot...")
    bot.run()
