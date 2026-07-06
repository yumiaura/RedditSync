"""Record an already-published post so the auto-publisher never reposts it."""
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import published_store

ALREADY_SENT = [
    {
        "reddit_id": "1uo0dx2",
        "subreddit": "ProgrammerHumor",
        "title": "somebodyTouchaMySpaghet",
        "permalink": "https://reddit.com/r/ProgrammerHumor/comments/"
                     "1uo0dx2/somebodytouchamyspaghet/",
        "telegram_message_id": 5,
    },
]


def main():
    load_dotenv()
    connection = published_store.open_store()
    try:
        for record in ALREADY_SENT:
            published_store.mark_published(
                connection,
                record["reddit_id"],
                record["subreddit"],
                record["title"],
                record["permalink"],
                record["telegram_message_id"],
            )
            print(f"recorded {record['reddit_id']} "
                  f"(message_id={record['telegram_message_id']}) as published")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
