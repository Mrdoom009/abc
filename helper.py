import os
import subprocess
import mmap
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import logging
import datetime
import asyncio
import requests
import time
import aiohttp
import aiofiles
import concurrent.futures
from pyrogram.types import Message
from pyrogram import Client
from pathlib import Path
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import tempfile

# Same AES Key aur IV jo encryption ke liye use kiya tha
KEY = b"^#^#&@*HDU@&@*()"
IV = b"^@%#&*NSHUE&$*#)"

# Decryption function
def dec_url(enc_url):
    enc_url = enc_url.replace("helper://", "")  # "helper://" prefix hatao
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    decrypted = unpad(cipher.decrypt(b64decode(enc_url)), AES.block_size)
    return decrypted.decode("utf-8")


# Function to split name & Encrypted URL properly
def split_name_enc_url(line):
    match = re.search(
        r"(helper://\S+)", line
    )  # Find `helper://` ke baad ka encrypted URL
    if match:
        name = (
            line[: match.start()].strip().rstrip(":")
        )  # Encrypted URL se pehle ka text
        enc_url = match.group(1).strip()  # Sirf Encrypted URL
        return name, enc_url
    return line.strip(), None  # Agar encrypted URL nahi mila, to pura line name maan lo


# Function to decrypt file URLs
def decrypt_file_txt(input_file):
    output_file = "decrypted_" + input_file  # Output file ka naam

    # Ensure the directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_file, "r", encoding="utf-8") as f, open(
        output_file, "w", encoding="utf-8"
    ) as out:
        for line in f:
            name, enc_url = split_name_enc_url(
                line
            )  # Sahi tarike se name aur encrypted URL split karo
            if enc_url:
                dec = dec_url(enc_url)  # Decrypt URL
                out.write(f"{name}: {dec}\n")  # Ek hi `:` likho
            else:
                out.write(
                    line.strip() + "\n"
                )  # Agar encrypted URL nahi mila to line jaisa hai waisa likho

    return output_file  # Decrypted file ka naam return karega


async def duration(filename):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        filename,
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    return float(stdout.decode().strip())


async def get_mps_and_keys(api_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            response_json = await response.json()
            mpd = response_json.get("MPD")
            keys = response_json.get("KEYS")
            return mpd, keys


async def exec(cmd):
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    output = stdout.decode()
    return output


async def pull_run(work, cmds):
    tasks = []
    for cmd in cmds:
        tasks.append(exec(cmd))
    
    await asyncio.gather(*tasks)


async def download(url, name):
    ka = f"{name}.pdf"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(ka, mode="wb") as f:
                    await f.write(await resp.read())
    return ka


async def pdf_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
        
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            async with aiofiles.open(file_name, "wb") as fd:
                async for chunk in response.content.iter_chunked(chunk_size):
                    await fd.write(chunk)
    return file_name


def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and "---" not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 2)
            try:
                if (
                    "RESOLUTION" not in i[2]
                    and i[2] not in temp
                    and "audio" not in i[2]
                ):
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info


def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and "---" not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 3)
            try:
                if (
                    "RESOLUTION" not in i[2]
                    and i[2] not in temp
                    and "audio" not in i[2]
                ):
                    temp.append(i[2])
                    new_info.update({f"{i[2]}": f"{i[0]}"})
            except:
                pass
    return new_info


async def decrypt_and_merge_video(
    mpd_url, keys_string, output_path, output_name, quality="720"
):
    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Download video
        cmd1 = f'yt-dlp -f "bv[height<={quality}]+ba/b" -o "{output_path}/file.%(ext)s" --allow-unplayable-format --no-check-certificate --external-downloader aria2c "{mpd_url}"'
        await exec(cmd1)

        avDir = list(output_path.iterdir())
        print(f"Downloaded files: {avDir}")
        print("Decrypting")

        video_decrypted = False
        audio_decrypted = False

        for data in avDir:
            if data.suffix == ".mp4" and not video_decrypted:
                cmd2 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/video.mp4"'
                await exec(cmd2)
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                data.unlink()
            elif data.suffix == ".m4a" and not audio_decrypted:
                cmd3 = f'mp4decrypt {keys_string} --show-progress "{data}" "{output_path}/audio.m4a"'
                await exec(cmd3)
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                data.unlink()

        if not video_decrypted or not audio_decrypted:
            raise FileNotFoundError("Decryption failed: video or audio file not found.")

        # Merge video and audio
        cmd4 = f'ffmpeg -i "{output_path}/video.mp4" -i "{output_path}/audio.m4a" -c copy "{output_path}/{output_name}.mp4"'
        await exec(cmd4)
        
        # Cleanup
        if (output_path / "video.mp4").exists():
            (output_path / "video.mp4").unlink()
        if (output_path / "audio.m4a").exists():
            (output_path / "audio.m4a").unlink()

        filename = output_path / f"{output_name}.mp4"

        if not filename.exists():
            raise FileNotFoundError("Merged video file not found.")

        return str(filename)

    except Exception as e:
        print(f"Error during decryption and merging: {str(e)}")
        raise


async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    print(f"[{cmd!r} exited with {proc.returncode}]")
    if proc.returncode == 1:
        return False
    if stdout:
        return f"[stdout]\n{stdout.decode()}"
    if stderr:
        return f"[stderr]\n{stderr.decode()}"


def human_readable_size(size, decimal_places=2):
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024.0 or unit == "PB":
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


async def download_video(url, cmd, name):
    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --external-downloader aria2c --downloader-args "aria2c: -x 16 -j 32"'
    
    try:
        process = await asyncio.create_subprocess_shell(
            download_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Capture stdout and stderr
        stdout, stderr = await process.communicate()
        
        # Check for errors
        if process.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            logging.error(f"Download failed for {name}: {error_msg}")
            return None
        
        # Check for downloaded files
        for ext in ["", ".webm", ".mkv", ".mp4", ".mp4.webm"]:
            file_path = f"{name}{ext}"
            if os.path.isfile(file_path):
                return file_path
        
        logging.warning(f"No valid file found for {name} after download")
        return None
        
    except Exception as e:
        logging.error(f"Exception in download_video for {name}: {str(e)}")
        return None

async def send_doc(bot: Client, msg: Message, cc, ka, cc1, count, name):
    reply = await msg.reply_text(f"Uploading - `{name}`")
    try:
        await msg.reply_document(ka, caption=cc1)
        count += 1
    finally:
        await reply.delete()
        if os.path.exists(ka):
            os.remove(ka)


def decrypt_file(file_path, key):
    if not os.path.exists(file_path):
        return False

    with open(file_path, "r+b") as f:
        num_bytes = min(28, os.path.getsize(file_path))
        with mmap.mmap(
            f.fileno(), length=num_bytes, access=mmap.ACCESS_WRITE
        ) as mmapped_file:
            for i in range(num_bytes):
                mmapped_file[i] ^= ord(key[i]) if i < len(key) else i
    return True


async def download_and_decrypt_video(url, cmd, name, key):
    video_path = await download_video(url, cmd, name)
    if video_path and decrypt_file(video_path, key):
        return video_path
    return None


async def download_and_decrypt_pdf(url, name, key):
    download_cmd = f'yt-dlp -o "{name}.pdf" "{url}" -R 25 --fragment-retries 25'
    process = await asyncio.create_subprocess_shell(download_cmd)
    await process.wait()
    
    file_path = f"{name}.pdf"
    if os.path.exists(file_path) and decrypt_file(file_path, key):
        return file_path
    return None


# -----------------------Emoji handler------------------------------------

EMOJIS = ["🔥", "💥", "👨‍❤️‍💋‍👨", "👱🏻", "👻", "⚡", "💫", "🐟", "🦅", "🌹", "🦋"]
emoji_counter = 0  # Initialize a global counter


def get_next_emoji():
    global emoji_counter
    emoji = EMOJIS[emoji_counter]
    emoji_counter = (emoji_counter + 1) % len(EMOJIS)
    return emoji


async def send_vid(bot: Client, msg: Message, cc, filename, thumb, name, prog):
    emoji = get_next_emoji()
    
    # Generate thumbnail asynchronously
    thumbnail_path = f"{filename}.jpg"
    thumb_process = await asyncio.create_subprocess_shell(
        f'ffmpeg -i "{filename}" -ss 00:00:02 -vframes 1 "{thumbnail_path}"'
    )
    await thumb_process.wait()
    
    await prog.delete()
    reply = await m.reply_text(f"🚀🚀𝗨𝗣𝗟𝗢𝗔𝗗𝗜𝗡𝗚🚀🚀🚀** » `{name}`\n\n🤖𝗕𝗢𝗧 𝗠𝗔𝗗𝗘 𝗕𝗬 ➤ 𝗧𝗨𝗦𝗛𝗔𝗥")

    try:
        if thumb == "no" and os.path.exists(thumbnail_path):
            thumbnail = thumbnail_path
        else:
            thumbnail = thumb
            
        dur = await duration(filename)
        processing_msg = await m.reply_text(emoji)

        try:
            await msg.reply_video(
                filename,
                caption=cc,
                supports_streaming=True,
                height=720,
                width=1280,
                thumb=thumbnail,
                duration=dur,
                progress=progress_bar,
                progress_args=(reply, time.time()),
            )
        except Exception:
            await msg.reply_document(
                filename,
                caption=cc,
                progress=progress_bar,
                progress_args=(reply, time.time()),
            )
            
    finally:
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        await processing_msg.delete()
        await reply.delete()


async def watermark_pdf(file_path, watermark_text):
    def create_watermark(text):
        packet = BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        width, height = letter
        can.setFont("Helvetica", 40)
        can.setFillColorRGB(0.6, 0.6, 0.6, alpha=0.5)
        can.saveState()
        can.translate(width / 2, height / 2)
        can.rotate(45)
        lines = text.split("\n")
        line_height = 50
        for i, line in enumerate(lines):
            text_width = can.stringWidth(line, "Helvetica", 40)
            can.drawString(-text_width / 2, -i * line_height, line)
        can.restoreState()
        can.save()
        packet.seek(0)
        return PdfReader(packet)

    # Create watermark PDF
    watermark = create_watermark(watermark_text)
    reader = PdfReader(file_path)
    writer = PdfWriter()

    # Add watermark to each page
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]
        watermark_page = watermark.pages[0]
        page.merge_page(watermark_page)
        writer.add_page(page)

    # Output file
    new_file_path = file_path.replace(".pdf", "_.pdf")
    with open(new_file_path, "wb") as out_file:
        writer.write(out_file)

    # Delete the original file
    os.remove(file_path)

    return new_file_path
