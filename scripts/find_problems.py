#!/usr/bin/env python3

"""
Find and diagnose any problems coming up in the next 30 days.
"""

from datetime import timedelta
import sys
import json
import logging
import os
import re

import boto3
from dateutil.parser import parse as dateutil_parse
import redis
import requests
import PIL.Image as Image

dynamodb = boto3.resource("dynamodb")
logger = logging.getLogger(__name__)
number_regex = re.compile(r"[0-9]")

CONFIG_JSON = "lambdas/biblein1year_main/config.json"

ALLOWED_ASPECT_RATIOS = {
    0.52, 0.55, 0.56,
    0.68, 0.69,
    0.72, 0.75, 0.78,
    0.8, 1,
}


def get_last_updated():
    with open(CONFIG_JSON) as fh:
        config = json.load(fh)
    redis_client = redis.from_url(config["redis_url"])
    return dateutil_parse(redis_client.get("last_updated_date")).date()


def get_relevant_dates(last_updated, days):
    one_day = timedelta(days=1)
    start_date = last_updated + one_day
    end_date = start_date + (one_day * days)
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


class DummyLog:
    def __init__(self):
        self.cache = []

    def warn(self, msg):
        self.cache.append([logging.WARNING, msg])

    def error(self, msg):
        self.cache.append([logging.ERROR, msg])

    def output(self, date, real_logger):
        if len(self.cache):
            print(date)
            for level, msg in self.cache:
                real_logger.log(level, msg)


abbreviations_cache = set()


def find_abbreviation(book_short):
    abbreviations = dynamodb.Table("abbreviations")
    if book_short in abbreviations_cache:
        return True
    response = abbreviations.get_item(
        Key={"book_short": book_short.lower()},
    )
    if response.get("Item"):
        abbreviations_cache.add(book_short)
        return True
    else:
        return False


def ensure_short_ref(reading, log_func):
    book_short = number_regex.split(reading["ref"])[0].strip()
    if not find_abbreviation(book_short):
        log_func("No short reference found for '{}'".format(book_short))
        return False
    return True


def check_for_image_url(reading, log_func):
    if reading.get("image_url") is None:
        log_func("No image URL for {}".format(reading["ref"]))
        return False
    return True


def check_image_aspect_ratio(reading, log_func):
    response = requests.get(reading["image_url"], stream=True)
    response.raw.decode_content = True
    img = Image.open(response.raw)
    x2, x1 = img.size
    ratio = round(x1 / x2, 2)
    if not (0.78 < ratio < 1) and ratio not in ALLOWED_ASPECT_RATIOS:
        log_func(f"Aspect ratio of {ratio} is not supported for ref {reading['ref']}.")
        return False
    return True


def main(days_to_fetch=30):
    try:
        last_updated = get_last_updated()
    except Exception:
        return os.linesep.join([
            "Cannot fetch last_updated_date. Please ensure:",
            " - That the file {} exists and contains a valid 'redis_url' entry".format(CONFIG_JSON),
            " - That the Redis server contains a key called 'last_updated_date'",
            " - That the above key is formatted correctly",
        ])

    readings = dynamodb.Table("readings")

    for date in get_relevant_dates(last_updated, days_to_fetch):
        log = DummyLog()
        response = readings.get_item(
            Key={"month": date.month, "day": date.day},
        )
        item = response["Item"]
        for reading in item["data"]:
            ensure_short_ref(reading, log.warn)
            if check_for_image_url(reading, log.error):
                check_image_aspect_ratio(reading, log.error)
        log.output(date, logger)


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("  %(levelname).1s:%(message)s"))
    logger.addHandler(handler)
    sys.exit(main(*[int(a) for a in sys.argv[1:]]))
