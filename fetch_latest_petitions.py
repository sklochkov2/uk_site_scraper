#!/usr/bin/python3

import asyncio
import html
import os
import requests
import telegram
from time import sleep


def fetch_last_id(path):
    f = open(path)
    res = f.read().strip()
    f.close()
    return int(res)


def save_last_id(path, pid):
    f = open(path, "w")
    f.write(str(pid))
    f.close()


def fetch_text_from_url(url):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text.split("\n")


def fetch_value_from_line(line):
    parts = line.split('"')
    if len(parts) >= 4:
        return html.unescape(parts[3])
    return ""


def fetch_petition_by_id(pid):
    url = f"https://petition.parliament.uk/petitions/{pid}/gathering-support"
    retries = 3
    pet_text = []
    while retries:
        try:
            pet_text = fetch_text_from_url(url)
            break
        except requests.HTTPError:
            return None
        except:
            retries -= 1
            sleep(1)
    header = ""
    body = ""
    for line in pet_text:
        if line.find("og:title") != -1:
            header = fetch_value_from_line(line)
        elif line.find("og:description") != -1:
            body = fetch_value_from_line(line)
    if not (header or body):
        return {}
    return {"h": header, "b": body, "id": pid}


def fetch_petitions(path):
    pid = fetch_last_id(path)
    res = []
    while True:
        try:
            curr = fetch_petition_by_id(pid)
            if curr is None:
                break
            if curr:
                res.append(curr)
        except:
            pass
        pid += 1
        sleep(1)
    save_last_id(path, pid)
    return res


def format_petition(pet):
    pid = pet["id"]
    header = telegram.helpers.escape_markdown(pet["h"], version=2)
    body = telegram.helpers.escape_markdown(pet["b"], version=2)
    link_text = telegram.helpers.escape_markdown(f"Petition {pid}", version=2)
    link = f"https://petition.parliament.uk/petitions/{pid}"
    return f"[{link_text}]({link})\n\n{header}\n\n{body}"


async def send_messages(pets, token, chat_id):
    bot = telegram.Bot(token=token)
    for pet in pets:
        await bot.send_message(
            chat_id=chat_id,
            text=format_petition(pet),
            parse_mode=telegram.constants.ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
        # Avoid getting into telegram rate limit
        sleep(2)


def main():
    path = "./id.txt"
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    try:
        pets = fetch_petitions(path)
        for pet in pets:
            print("Petition %s\n%s\n%s\n" % (pet["id"], pet["h"], pet["b"]))
        asyncio.run(send_messages(pets, token, chat_id))
    except Exception as ex:
        print("Failed to fetch petitions:", ex)


if __name__ == "__main__":
    main()
