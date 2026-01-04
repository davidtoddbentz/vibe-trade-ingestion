"""Canonical tweet model."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Tweet:
    """Twitter/X tweet data."""

    tweet_id: str
    user_id: str
    username: str
    text: str
    timestamp: datetime
    url: str | None = None
    source: str | None = None
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    lang: str | None = None
    bookmark_count: int = 0
    is_reply: bool = False
    in_reply_to_id: str | None = None
    conversation_id: str | None = None
    in_reply_to_user_id: str | None = None
    in_reply_to_username: str | None = None
    entities: dict | None = None  # hashtags, urls, user_mentions
    quoted_tweet: dict | None = None
    retweeted_tweet: dict | None = None
    is_limited_reply: bool = False
