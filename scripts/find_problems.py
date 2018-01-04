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

dynamodb = boto3.resource("dynamodb")
logger = logging.getLogger(__name__)
number_regex = re.compile(r"[0-9]")

CONFIG_JSON = "lambdas/biblein1year_main/config.json"


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


def main():
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

    for date in get_relevant_dates(last_updated, 30):
        to_log = []
        response = readings.get_item(
            Key={"month": date.month, "day": date.day},
        )
        item = response["Item"]
        for reading in item["data"]:
            book_short = number_regex.split(reading["ref"])[0].strip()
            if not find_abbreviation(book_short):
                to_log.append([
                    logging.WARNING,
                    "No short reference found for '{}'".format(book_short),
                ])
            if reading.get("image_url") is None:
                to_log.append([
                    logging.ERROR, "No image URL for {}".format(reading["ref"])
                ])
        if to_log:
            print(date)
            for level, msg in to_log:
                logger.log(level, msg)


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("  %(levelname).1s:%(message)s"))
    logger.addHandler(handler)
    sys.exit(main())
