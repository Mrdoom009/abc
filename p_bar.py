import time
import math
import os
from pyrogram.errors import FloodWait
from pyrogram import enums
from datetime import datetime, timedelta


class Timer:
    def __init__(self, time_between=5):
        self.start_time = time.time()
        self.time_between = time_between

    def can_send(self):
        if time.time() > (self.start_time + self.time_between):
            self.start_time = time.time()
            return True
        return False


# Function to convert bytes to a human-readable format
def hrb(value, digits=2, delim="", postfix=""):
    if value is None:
        return None
    chosen_unit = "B"
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        if value > 1000:
            value /= 1024
            chosen_unit = unit
        else:
            break
    return f"{value:.{digits}f}" + delim + chosen_unit + postfix


# Function to convert seconds to a human-readable time format
def hrt(seconds, precision=0):
    pieces = []
    value = timedelta(seconds=seconds)

    if value.days:
        pieces.append(f"{value.days}d")

    seconds = value.seconds

    if seconds >= 3600:
        hours = int(seconds / 3600)
        pieces.append(f"{hours}h")
        seconds -= hours * 3600

    if seconds >= 60:
        minutes = int(seconds / 60)
        pieces.append(f"{minutes}m")
        seconds -= minutes * 60

    if seconds > 0 or not pieces:
        pieces.append(f"{seconds}s")

    if not precision:
        return "".join(pieces)

    return "".join(pieces[:precision])


timer = Timer()

# Designed by Mendax
async def progress_bar(current, total, reply, start):
    if timer.can_send():
        now = time.time()
        diff = now - start
        if diff < 1:
            return

        perc = f"{current * 100 / total:.1f}%"
        elapsed_time = round(diff)
        speed = current / elapsed_time if elapsed_time > 0 else 0
        remaining_bytes = total - current

        if speed > 0:
            eta_seconds = remaining_bytes / speed
            eta = hrt(eta_seconds, precision=1)
        else:
            eta = "-"

        sp = str(hrb(speed)) + "/s"
        tot = hrb(total)
        cur = hrb(current)

        # Don't even change anything till here
        # Calculate progress bar dots
        bar_length = 10
        completed_length = int(current * bar_length / total)
        remaining_length = bar_length - completed_length
        progress_bar = "🟢" * completed_length + "🔴" * remaining_length

        try:
            await reply.edit(
                f"╭──◈◈◈◈**Uᴘʟσᴅɪɴɢ**◈◈◈◈──╮\n├⚡ {progress_bar}\n├🚀 Sᴘєєᴅ ➠ {sp}\n├📛 Pʀσɢʀєss ➠ {perc}\n├📟 Dσɴє ➠ {cur}\n├🧲 Sɪᴢє ➠ {tot}\n├🕑 Eᴛα ➠ {eta}\n╰─◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈◈─╯"
            )
        except FloodWait as e:
            time.sleep(e.x)
    
