"""Caption formatting tests for telegram_publisher.build_caption."""
import re

import telegram_publisher

EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF❤]")


def test_caption_layout_bold_title_and_subreddit_link():
    caption = telegram_publisher.build_caption(
        "It works on my machine", "ProgrammerHumor",
        "https://reddit.com/r/ProgrammerHumor/comments/1def45/it_works/")
    assert caption == (
        "<b>It works on my machine</b>\n"
        '<a href="https://reddit.com/r/ProgrammerHumor/comments/1def45/'
        'it_works/">r/ProgrammerHumor</a>'
    )


def test_title_is_html_escaped():
    caption = telegram_publisher.build_caption(
        'When you write <div> & "forget" to close it', "ProgrammerHumor",
        "https://reddit.com/r/ProgrammerHumor/comments/1abc23/")
    first_line = caption.split("\n")[0]
    assert first_line == (
        "<b>When you write &lt;div&gt; &amp; "
        "&quot;forget&quot; to close it</b>")
    # no raw < or & from the title survives inside the bold tag
    assert "<div>" not in caption


def test_caption_adds_no_emoji():
    caption = telegram_publisher.build_caption(
        "Plain title", "linuxmemes",
        "https://reddit.com/r/linuxmemes/comments/1xyz11/")
    assert EMOJI_RE.search(caption) is None


def test_subreddit_link_text_format():
    caption = telegram_publisher.build_caption(
        "T", "funnyAnimals", "https://reddit.com/r/funnyAnimals/comments/1a2b3c/")
    link_line = caption.split("\n")[1]
    assert link_line.endswith(">r/funnyAnimals</a>")
    assert link_line.startswith('<a href="https://reddit.com/')
