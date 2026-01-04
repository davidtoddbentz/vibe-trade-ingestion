"""Twitter/X API adapter for fetching user tweets."""

import logging
from datetime import datetime, timezone

import requests
from dateutil import parser

from ..models.tweet import Tweet

logger = logging.getLogger(__name__)


class TwitterAPIError(Exception):
    """Base exception for Twitter API errors."""
    pass


class TwitterAPIAdapter:
    """Twitter/X API adapter using TwitterAPI.io."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.twitterapi.io",
    ):
        """Initialize Twitter API adapter.

        Args:
            api_key: TwitterAPI.io API key
            base_url: Base URL for TwitterAPI.io (default: https://api.twitterapi.io)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": api_key,
        }

    def get_user_last_tweets(
        self,
        username: str | None = None,
        user_id: str | None = None,
        cursor: str = "",
        include_replies: bool = False,
    ) -> dict:
        """Get last tweets from a user.

        Args:
            username: Twitter username (without @)
            user_id: Twitter user ID (preferred over username)
            cursor: Pagination cursor (empty string for first page)
            include_replies: Whether to include replies

        Returns:
            API response with tweets, has_next_page, next_cursor, status

        Raises:
            TwitterAPIError: If API request fails
        """
        if not username and not user_id:
            raise ValueError("Either username or user_id must be provided")

        url = f"{self.base_url}/twitter/user/last_tweets"
        params = {
            "cursor": cursor,
            "includeReplies": str(include_replies).lower(),
        }

        if user_id:
            params["userId"] = user_id
        else:
            params["userName"] = username.lstrip("@")

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Twitter API request failed: {e}")
            raise TwitterAPIError(f"Failed to fetch tweets: {e}") from e

    def parse_tweet(self, tweet_data: dict) -> Tweet | None:
        """Parse API tweet response into Tweet model.

        Args:
            tweet_data: Raw tweet data from API

        Returns:
            Tweet object or None if parsing fails
        """
        try:
            # Parse timestamp
            created_at = tweet_data.get("createdAt")
            if created_at:
                try:
                    timestamp = parser.isoparse(created_at)
                except (ValueError, TypeError):
                    timestamp = parser.parse(created_at)
            else:
                timestamp = datetime.now(timezone.utc)

            # Get author info
            author = tweet_data.get("author", {})
            username = author.get("userName", "")
            user_id = author.get("id", "")

            # Get retweeted/quoted tweet info
            retweeted_tweet = tweet_data.get("retweeted_tweet")
            quoted_tweet = tweet_data.get("quoted_tweet")

            return Tweet(
                tweet_id=tweet_data.get("id", ""),
                user_id=user_id,
                username=username,
                text=tweet_data.get("text", ""),
                timestamp=timestamp,
                url=tweet_data.get("url"),
                source=tweet_data.get("source"),
                retweet_count=tweet_data.get("retweetCount", 0),
                reply_count=tweet_data.get("replyCount", 0),
                like_count=tweet_data.get("likeCount", 0),
                quote_count=tweet_data.get("quoteCount", 0),
                view_count=tweet_data.get("viewCount", 0),
                lang=tweet_data.get("lang"),
                bookmark_count=tweet_data.get("bookmarkCount", 0),
                is_reply=tweet_data.get("isReply", False),
                in_reply_to_id=tweet_data.get("inReplyToId"),
                conversation_id=tweet_data.get("conversationId"),
                in_reply_to_user_id=tweet_data.get("inReplyToUserId"),
                in_reply_to_username=tweet_data.get("inReplyToUsername"),
                entities=tweet_data.get("entities"),
                quoted_tweet=quoted_tweet if isinstance(quoted_tweet, dict) else None,
                retweeted_tweet=retweeted_tweet if isinstance(retweeted_tweet, dict) else None,
                is_limited_reply=tweet_data.get("isLimitedReply", False),
            )
        except Exception as e:
            logger.error(f"Error parsing tweet: {e}", exc_info=True)
            return None

    def get_new_tweets_since(
        self,
        username: str | None = None,
        user_id: str | None = None,
        since_timestamp: datetime | None = None,
        include_replies: bool = False,
    ) -> list[Tweet]:
        """Get new tweets since a timestamp.

        Args:
            username: Twitter username (without @)
            user_id: Twitter user ID (preferred)
            since_timestamp: Only return tweets after this timestamp
            include_replies: Whether to include replies

        Returns:
            List of new Tweet objects
        """
        tweets = []
        cursor = ""
        has_next_page = True

        while has_next_page:
            try:
                response = self.get_user_last_tweets(
                    username=username,
                    user_id=user_id,
                    cursor=cursor,
                    include_replies=include_replies,
                )

                if response.get("status") != "success":
                    logger.error(f"API returned error: {response.get('message')}")
                    break

                tweet_list = response.get("tweets", [])
                for tweet_data in tweet_list:
                    tweet = self.parse_tweet(tweet_data)
                    if tweet:
                        # Stop if we've reached tweets older than since_timestamp
                        if since_timestamp and tweet.timestamp <= since_timestamp:
                            has_next_page = False
                            break
                        tweets.append(tweet)

                has_next_page = response.get("has_next_page", False)
                cursor = response.get("next_cursor", "")

                # If we have a since_timestamp and the oldest tweet is newer, we can stop
                if since_timestamp and tweets:
                    oldest_tweet = min(tweets, key=lambda t: t.timestamp)
                    if oldest_tweet.timestamp <= since_timestamp:
                        break

            except TwitterAPIError as e:
                logger.error(f"Error fetching tweets: {e}")
                break

        return tweets

