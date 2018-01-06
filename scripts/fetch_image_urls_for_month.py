#!/usr/bin/env python3

import sys
import warnings

import boto3
from boto3.dynamodb.conditions import Key
import requests

dynamodb = boto3.resource("dynamodb")


def fetch_image_urls_for_month(month):
    table = dynamodb.Table("readings")
    response = table.query(
        KeyConditionExpression=Key("month").eq(month),
    )
    for day in response["Items"]:
        updated = False
        for reading in day["data"]:
            ref = reading["ref"].replace(" ", "")
            image_url = "https://biblia.com/verseoftheday/image/{}".format(ref)
            response = requests.head(image_url)
            if response.status_code != 200:
                warnings.warn("Ref without image: {}\t({}/{})".format(
                    reading["ref"], day["day"], month,
                ))
                continue
            if reading.get("image_url") != image_url:
                reading["image_url"] = image_url
                updated = True

        if updated:
            print("Updating data for {}/{}...".format(day["day"], month))
            table.update_item(
                Key={
                    "month": day["month"],
                    "day": day["day"],
                },
                UpdateExpression="SET #d = :val1",
                ExpressionAttributeNames={
                    "#d": "data",
                },
                ExpressionAttributeValues={
                    ":val1": day["data"],
                },
            )


def main(argv):
    try:
        month, = argv
    except ValueError:
        return "Usage: {} month_number".format(sys.argv[0])
    try:
        month = int(month)
    except ValueError:
        return "Error: Month '{}' is not numeric".format(month)
    if month < 1 or month > 12:
        return "Error: Month must be between 1 and 12"
    fetch_image_urls_for_month(month)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
