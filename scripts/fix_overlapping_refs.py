#!/usr/bin/env python3

import operator
import re
import sys
from urllib.parse import quote_plus

import boto3
import requests

dynamodb = boto3.resource("dynamodb")

VERSE_REGEX = re.compile(r"(\d?\s?[a-zA-Z ]+)\s?(\d+:?\d*[a-z]?)-?(\d+:?\d*[a-z]?)?")
BIBLE_URL_PATTERN = "http://labs.bible.org/api/?passage={passage}&type=json"

ONE_CHAPTER_BOOKS = frozenset({"Obadiah", "Philemon", "2 John", "3 John", "Jude"})


class Verse(str):

    def __new__(cls, book, chapter_verse):
        obj = str.__new__(cls, f"{book} {chapter_verse}")
        obj.book = book
        try:
            chapter, verse = chapter_verse.split(":")
        except ValueError:
            chapter = chapter_verse
            verse = None
        obj.chapter = chapter
        obj.verse = verse
        return obj


class VerseRange:

    """
    >>> VerseRange("John 3:16")
    <VerseRange: John 3:16>
    >>> VerseRange("1 John 3:16")
    <VerseRange: 1 John 3:16>
    """

    def __init__(self, ref_str: str):
        self.str = ref_str
        if ref_str in ONE_CHAPTER_BOOKS:
            ref_str = f"{ref_str} 1"  # make it parse
        match = VERSE_REGEX.match(ref_str)
        if match is None:
            raise re.error(f"'{ref_str}' does not match regex!")
        book, first, last = match.groups()
        self.first = Verse(book.strip(), first)
        self.last = Verse(book.strip(), last) if last else None

    def __repr__(self):
        if self.last:
            return f"<VerseRange: {self.first} ... {self.last}>"
        else:
            return f"<VerseRange: {self.first}>"


def get_refs_from_data(data):
    if len(data) == 2:
        old, new = data
        ps_pr = None
    else:
        old, new, ps_pr = data
    old = VerseRange(old["ref"])
    new = VerseRange(new["ref"])
    if ps_pr:
        ps_pr = VerseRange(ps_pr["ref"])
    return old, new, ps_pr


def find_overlaps(table):
    items = table.scan()["Items"]
    prev_old = prev_new = prev_ps_pr = None
    for item in sorted(items, key=operator.itemgetter("month", "day")):
        old, new, ps_pr = get_refs_from_data(item["data"])
        overlaps = [None] * 3
        if prev_old and prev_old.last == old.first:
            overlaps[0] = old
        if prev_new and prev_new.last == new.first:
            overlaps[1] = new
        if prev_ps_pr and ps_pr and prev_ps_pr.last == ps_pr.first:
            overlaps[2] = ps_pr
        if any(overlaps):
            yield overlaps, item
        prev_old = old
        prev_new = new
        if ps_pr:
            prev_ps_pr = ps_pr


def main(argv):
    if len(argv):
        return "This command takes no arguments"
    table = dynamodb.Table("readings")
    for overlaps, day in find_overlaps(table):
        for i, ref in enumerate(overlaps):
            if ref is None:
                continue
            resp = requests.get(BIBLE_URL_PATTERN.format(passage=quote_plus(ref.str)))
            if not resp.ok:
                raise Exception(f"Response failed: {resp.status_code} {resp.reason}")
            new_verse = resp.json()[1]
            if new_verse["chapter"] == ref.last.chapter:
                new_ref = "{book} {chapter}:{verse1}-{verse2}".format(
                    book=ref.first.book,
                    chapter=new_verse["chapter"],
                    verse1=new_verse["verse"],
                    verse2=ref.last.verse,
                )
            else:
                new_ref = "{book} {chapter1}:{verse1}-{chapter2}:{verse2}".format(
                    book=ref.first.book,
                    chapter1=new_verse["chapter"],
                    verse1=new_verse["verse"],
                    chapter2=ref.last.chapter,
                    verse2=ref.last.verse,
                )
            day["data"][i]["ref.old-overlap"] = day["data"][i]["ref"]
            day["data"][i]["ref"] = new_ref
        print("Updating data for {}/{}...".format(day["day"], day["month"]))
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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
