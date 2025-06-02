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
task_status = {}

cyt = "https://graph.org/file/996d4fc24564509244988-a7d93d020c96973ba8.jpg"
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
token_cp = "eyJjb3Vyc2VJZCI6IjQ1NjY4NyIsInR1dG9ySWQiOm51bGwsIm9yZ2lkIjo0ODA2MTksImNhdGVnb3J5SWQiOm51bGx9gft"

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

async def show_random_emojis(msg: Message):
    emojis = [
        "🎊", "🔮", "😎", "⚡️", "🚀", "✨", "💥", "🎉", "🥂", "🍾", 
        "🦠", "🤖", "❤️‍🔥", "🕊️", "💃", "🥳", "🐅", "🦁",
    ]
    emoji_message = await msg.reply_text(" ".join(random.choices(emojis, k=1)))
    return emoji_message

async def cleanup_user_files(user_id: int):
    user_dir = f"./downloads/{user_id}"
    if os.path.exists(user_dir):
        try:
            shutil.rmtree(user_dir)
            return True
        except Exception as e:
            logging.error(f"Error cleaning files for user {user_id}: {str(e)}")
            return False
    return False

# Stop command handler - stops current user's operations
@bot.on_message(filters.command("stop"))
async def stop_handler(_, msg: Message):
    user_id = msg.from_user.id
    if user_id in user_tasks:
        user_tasks[user_id].cancel()
        del user_tasks[user_id]
        await msg.reply_text("⏹️ **Your operations have been stopped**")
        
        # Clean up user's downloaded files
        if await cleanup_user_files(user_id):
            await msg.reply_text("🧹 **Your downloaded files have been cleaned**")
    else:
        await msg.reply_text("ℹ️ **No active operations to stop**")

# Restart command handler - full bot restart (owner only)
@bot.on_message(filters.command("restart"))
async def restart_handler(_, msg: Message):
    if not is_authorized(msg.from_user.id):
        await msg.reply_text("**🚫 You are not authorized to use this command.**")
        return
    
    # Cancel all ongoing tasks
    for user_id, task in user_tasks.items():
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
        await message.reply_text("**🚫 You are not authorized to use this command.**")
        return

    try:
        args = message.text.split(" ", 2)
        if len(args) < 3:
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
        "`/txt` - Upload text files🎬\n\n"
        "`/restart` - Restart the bot🔮\n\n"
        "`/stop` - Stop ongoing process🛑\n\n"
        "`/sudo add` - Add sudo user (owner)🎊\n\n"
        "`/sudo remove` - Remove sudo user (owner)❌\n\n"
        "`/userlist` - List sudo users📜\n\n"
    )
    await msg.reply_text(help_text)

async def process_link(
    bot: Client,
    msg: Message,
    link: list,
    count: int,
    b_name: str,
    res: str,
    CR: str,
    thumb: str,
    user_dir: str,
    total_links: int
):
    user_id = msg.from_user.id
    try:
        V = (
            link[1]
            .replace("file/d/", "uc?export=download&id=")
            .replace("www.youtube-nocookie.com/embed", "youtu.be")
            .replace("?modestbranding=1", "")
            .replace("/view?usp=sharing", "")
        )
        url = "https://" + V

        # Handle special URL cases
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
                    url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)

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
            link[0]
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
        file_path = os.path.join(user_dir, f"{name}.mp4")

        # Show progress
        remaining_links = total_links - count
        progress = f"**🍁 DOWNLOADING 🍁**\n\n**📝 Name »** `{name}`\n\n🔗 Total URL » {total_links}\n\n🗂️ Index » {str(count)}/{total_links}\n\n🌐 Remaining URL » {remaining_links}\n\n❄ Quality » {res}\n\n**🔗 URL »** `{url}`\n\n🤖 BOT MADE BY ➤ TUSHAR"
        progress_msg = await msg.reply_text(progress)
        
        # Download and process the file
        if "youtu" in url:
            ytf = f"b[height<={res}][ext=mp4]/bv[height<={res}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
        else:
            ytf = f"b[height<={res}]/bv[height<={res}]+ba/b/bv+ba"

        cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{file_path}"'
        await helper.run_command(cmd)

        # Prepare caption
        caption = f"**[🎬] Vid_ID : {str(count).zfill(3)}.\n\n\n☘️ Title ➤ {name1}.({res}).Tushar.mkv\n\n\n<pre><code>📚 Batch ➤ {b_name}</code></pre>\n\n\n📥 Extracted By ➤ {CR}**"

        # Send the file
        if os.path.exists(file_path):
            await bot.send_video(
                chat_id=msg.chat.id,
                video=file_path,
                caption=caption,
                thumb=thumb if thumb != "no" else None,
                progress=progress_bar,
                progress_args=(progress_msg,)
            )
            os.remove(file_path)
            return True
        return False

    except Exception as e:
        logging.error(f"Error processing link: {str(e)}")
        await msg.reply_text(f"‼️ Download Failed ‼️\n\n📝 Name » `{name}`\n\n🔗 URL » `{url}`")
        return False
    finally:
        if 'progress_msg' in locals():
            await progress_msg.delete()

@bot.on_message(filters.command("txt"))
async def upload_handler(bot: Client, msg: Message):
    user_id = msg.from_user.id
    user_dir = f"./downloads/{user_id}"
    os.makedirs(user_dir, exist_ok=True)
    
    try:
        # Create task for cancellation
        task = asyncio.current_task()
        user_tasks[user_id] = task
        
        # Step 1: Get TXT file
        editable = await msg.reply_text("⚡ SEND TXT FILE ⚡")
        input_msg = await wait_for_message(msg.chat.id)
        if not input_msg or not input_msg.document:
            await editable.edit("**🚫 No file received. Process cancelled.**")
            return
        
        # Download TXT file
        txt_path = await input_msg.download(file_name=os.path.join(user_dir, "links.txt"))
        await input_msg.delete()
        
        # Log to channel
        user_info = f"👤 User ID: `{user_id}`"
        if msg.from_user.username:
            user_info += f"\n👤 Username: @{msg.from_user.username}"
        try:
            await bot.send_document(
                chat_id=LOG_CHANNEL,
                document=txt_path,
                caption=f"📝 New TXT file received\n{user_info}"
            )
        except Exception as e:
            logging.error(f"Failed to log TXT file: {str(e)}")
        
        # Process TXT file
        links = []
        with open(txt_path, "r") as f:
            for line in f:
                if "://" in line:
                    parts = line.split("://", 1)
                    if len(parts) == 2:
                        links.append(parts)
        os.remove(txt_path)
        
        if not links:
            await msg.reply_text("😶 No valid links found in the file")
            return
        
        # Step 2: Get starting index
        await editable.edit(f"Found {len(links)} links\nSend starting index (default: 1)")
        input0 = await wait_for_message(msg.chat.id)
        raw_text = input0.text if input0 else "1"
        try:
            start_index = max(1, min(int(raw_text), len(links)))
        except:
            start_index = 1
        
        # Step 3: Get batch name
        await editable.edit("📚 Enter Your Batch Name\nSend `1` for default")
        input1 = await wait_for_message(msg.chat.id)
        b_name = os.path.splitext(os.path.basename(txt_path))[0] if input1 and input1.text == "1" else (input1.text if input1 else "Default_Batch")
        
        # Step 4: Get resolution
        await editable.edit("**📸 Enter Resolution**\n➤ `144`\n➤ `240`\n➤ `360`\n➤ `480`\n➤ `720`\n➤ `1080`")
        input2 = await wait_for_message(msg.chat.id)
        res_map = {
            "144": "256x144",
            "240": "426x240",
            "360": "640x360",
            "480": "854x480",
            "720": "1280x720",
            "1080": "1920x1080"
        }
        res = res_map.get(input2.text if input2 else "", "UN")
        
        # Step 5: Get credit
        await editable.edit("📛 Enter Your Name\nSend `1` for default")
        input3 = await wait_for_message(msg.chat.id)
        CR = "️[Tushar](https://t.me/newstudent1885)"
        if input3 and input3.text != "1":
            try:
                text, link = input3.text.split(",", 1)
                CR = f"[{text.strip()}]({link.strip()})"
            except:
                CR = input3.text
        
        # Step 6: Get thumbnail
        await editable.edit("Send thumbnail URL or 'no' for no thumbnail")
        input6 = await wait_for_message(msg.chat.id)
        thumb = input6.text if input6 else "no"
        thumb_path = None
        
        if thumb.startswith("http"):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumb) as resp:
                        if resp.status == 200:
                            thumb_path = os.path.join(user_dir, 'thumb.jpg')
                            async with aiofiles.open(thumb_path, 'wb') as f:
                                await f.write(await resp.read())
            except:
                thumb_path = None
        
        await editable.delete()
        
        # Process links
        success_count = 0
        failed_count = 0
        total = len(links)
        
        for idx in range(start_index - 1, total):
            # Check for cancellation
            if user_id not in user_tasks or user_tasks[user_id].cancelled():
                await msg.reply_text("🛑 Operation stopped by user request")
                break
                
            result = await process_link(
                bot=bot,
                msg=msg,
                link=links[idx],
                count=idx+1,
                b_name=b_name,
                res=res,
                CR=CR,
                thumb=thumb_path or "no",
                user_dir=user_dir,
                total_links=total
            )
            
            if result:
                success_count += 1
            else:
                failed_count += 1
        
        # Send summary
        summary = (
            f"`✨ BATCH SUMMARY ✨\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"📚 Batch Name » {b_name}\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"✨ TXT SUMMARY ✨ : {total}\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"✅ Successful » {success_count}\n"
            f"❌ Failed » {failed_count}\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"✅ STATUS » COMPLETED`"
        )
        await msg.reply_text(summary)
        await msg.reply_text(f"<pre><code>📥 Extracted By ➤『{CR}』</code></pre>")
        
    except asyncio.CancelledError:
        await msg.reply_text("⏹️ Operation stopped by user request")
    except Exception as e:
        await msg.reply_text(f"❌ Unexpected error: {str(e)}")
    finally:
        # Cleanup
        if user_id in user_tasks:
            del user_tasks[user_id]
        await cleanup_user_files(user_id)

if __name__ == "__main__":
    bot.run()
