import re
import sys
import math
import os
import time

import requests
from bs4 import BeautifulSoup, Tag
import logging

formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",  # White
        "INFO": "\033[36m",  # Cyan
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def setup_custom_logger(name):
    formatter = ColorFormatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                               datefmt='%Y-%m-%d %H:%M:%S')

    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Remove any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(screen_handler)

    return logger


class Config:
    APPNAME = 'Beghir price'
    SITE_URL = 'https://tgju.org/'
    PROXY_ENABLED = True
    PROXIES = {
        'http': 'socks5h://127.0.0.1:2080',
        'https': 'socks5h://127.0.0.1:2080',
    }
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_ID')
    TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')


LOG = setup_custom_logger(Config.APPNAME)


def crawl_page():
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }

    response = requests.get(Config.SITE_URL, headers=headers, proxies=Config.PROXY_ENABLED)
    response.raise_for_status()
    return response.text


class ExtractPrices:
    _prices = [
        {"id": '#l-price_dollar_rl', "text": "دلار", 'price': 0, 'change_percentage': 0, 'unit': 'تومان'},
        {"id": '#l-sekee', "text": "سکه تمام امامی", 'price': 0, 'change_percentage': 0, 'unit': 'تومان'},
        {"id": '#l-mesghal', "text": "مثقال", 'price': 0, 'change_percentage': 0, 'unit': 'تومان'},
        {"id": '#l-ons', "text": "انس طلا", 'price': 0, 'change_percentage': 0, 'unit': 'دلار'},
        {"id": '#l-crypto-tether-irr', "text": "تتر", 'price': 0, 'change_percentage': 0, 'unit': 'تومان'},
        {"id": '#l-crypto-bitcoin', "text": "بیت کوین", 'price': 0, 'change_percentage': 0, 'unit': 'دلار'}
    ]

    def __init__(self, bs: BeautifulSoup):
        self.bs = bs

    def __clean_number(self, text: str) -> float:
        if not text:
            return 0.0
        text = re.sub(r"[^\d\.]", "", text)
        try:
            return float(text)
        except ValueError:
            return 0.0

    def __has_two_decimal_places(self, num: float) -> bool:
        return len(str(num).split('.')[-1]) == 2

    def __format_prices(self):
        lines = [r"*📊 قیمت‌ها امروز*", '\n',
                 "*قیمت های جدید رسید جنبه نداری نبین یوقت کپ می کنی می افتی رو دستمون حالا خربیار باقالی بار کن*",
                 '\n']
        for item in self._prices:
            price = item['price'] if not self.__has_two_decimal_places(item['price']) else math.ceil(item['price'])
            change = float(self.__clean_number(item['change_percentage']))

            if change > 0:
                emoji = "📈"
                change_text = f"+{change}%"
            elif change < 0:
                emoji = "📉"
                change_text = f"{change}%"
            else:
                emoji = "⏸️"

                change_text = "قمیتی ازش دردسترس نیست" if price == 0 else "بدون تغییر"

            lines.append(f"💰 {item['text']}: {int(price)} {item['unit']} {emoji} ({change_text})")

        return "\n".join(lines)

    def __get_price_in_block(self, section_id: str):
        section = self.bs.select_one(section_id)
        price = section.select_one('.info-price').text
        percentage_of_change = section.select_one('.info-change').text

        return price, percentage_of_change

    def get_prices(self, log):
        for p_details in self._prices:
            try:
                price, percentage_of_change = self.__get_price_in_block(p_details.get('id'))
                p_details.update(
                    {
                        "price": float(price.replace(',', '', 1000)),
                        "change_percentage": percentage_of_change
                    }
                )
            except Exception as e:
                LOG.error(repr(e))

        return self.__format_prices()


def extract_prices():
    page_content = crawl_page()
    bs = BeautifulSoup(page_content, 'html.parser')
    return ExtractPrices(bs).get_prices(LOG)


def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": Config.TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload, proxies=Config.PROXY_ENABLED)
    LOG.info(f'send to Telegram channel {response.json().get('ok')}')


def main():
    while True:
        LOG.info(f'job started')
        price_messages = extract_prices()
        send_to_telegram(price_messages)
        time.sleep(3600 / 12)


if __name__ == '__main__':
    main()
