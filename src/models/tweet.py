"""Canonical tweet model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Tweet:
    """Twitter/X tweet data."""

    tweet_id: str
    user_id: str
    username: str
    text: str
    timestamp: datetime
    url: Optional[str] = None
    source: Optional[str] = None
    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    view_count: int = 0
    lang: Optional[str] = None
    bookmark_count: int = 0
    is_reply: bool = False
    in_reply_to_id: Optional[str] = None
    conversation_id: Optional[str] = None
    in_reply_to_user_id: Optional[str] = None
    in_reply_to_username: Optional[str] = None
    entities: Optional[dict] = None  # hashtags, urls, user_mentions
    quoted_tweet: Optional[dict] = None
    retweeted_tweet: Optional[dict] = None
    is_limited_reply: bool = False

