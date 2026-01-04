"""Pub/Sub publisher for candle data."""

import json
import logging

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import types

from ..models.candle import Candle
from ..models.tweet import Tweet

logger = logging.getLogger(__name__)


class PubSubPublisher:
    """Publisher for sending candle data to GCP Pub/Sub."""

    def __init__(self, project_id: str):
        """Initialize Pub/Sub publisher.

        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        # Enable message ordering to support ordering keys
        publisher_options = types.PublisherOptions(enable_message_ordering=True)
        self.publisher = pubsub_v1.PublisherClient(publisher_options=publisher_options)

    def _get_topic_name(self, symbol: str, granularity: str = "1m") -> str:
        """Get Pub/Sub topic name for a symbol and granularity.

        Args:
            symbol: Trading symbol (e.g., "BTC-USD")
            granularity: Candle granularity (e.g., "1m")

        Returns:
            Topic name (e.g., "vibe-trade-candles-btc-usd-1m")
        """
        # Normalize symbol: BTC-USD -> btc-usd
        normalized_symbol = symbol.lower()
        return f"vibe-trade-candles-{normalized_symbol}-{granularity}"

    def _candle_to_message(self, symbol: str, candle: Candle) -> dict:
        """Convert candle to Pub/Sub message format.

        Args:
            symbol: Trading symbol
            candle: Candle data

        Returns:
            Message dictionary
        """
        return {
            "symbol": symbol,
            "timestamp": candle.timestamp.isoformat(),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
            "granularity": "1m",
        }

    def publish_candle(self, symbol: str, candle: Candle) -> str | None:
        """Publish a candle to Pub/Sub.

        Args:
            symbol: Trading symbol (e.g., "BTC-USD")
            candle: Candle data to publish

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            topic_name = self._get_topic_name(symbol)
            topic_path = self.publisher.topic_path(self.project_id, topic_name)

            # Convert candle to message
            message_data = self._candle_to_message(symbol, candle)
            message_json = json.dumps(message_data)

            # Publish with ordering key (symbol) to ensure order per symbol
            future = self.publisher.publish(
                topic_path,
                message_json.encode("utf-8"),
                ordering_key=symbol.lower(),  # Ensures messages for same symbol stay in order
            )

            message_id = future.result()
            logger.info(
                f"📤 Published candle to {topic_name}: {symbol} @ {candle.timestamp} "
                f"(message_id: {message_id})"
            )
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish candle for {symbol}: {e}", exc_info=True)
            return None

    def publish_candles(self, candles: dict[str, Candle]) -> dict[str, str | None]:
        """Publish multiple candles.

        Args:
            candles: Dictionary mapping symbol to candle

        Returns:
            Dictionary mapping symbol to message ID (or None if failed)
        """
        results = {}
        for symbol, candle in candles.items():
            if candle:
                message_id = self.publish_candle(symbol, candle)
                results[symbol] = message_id
            else:
                results[symbol] = None
        return results

    def _get_tweet_topic_name(self, username: str) -> str:
        """Get Pub/Sub topic name for a user's tweets.

        Args:
            username: Twitter username (e.g., "elonmusk")

        Returns:
            Topic name (e.g., "vibe-trade-tweets-elonmusk")
        """
        normalized_username = username.lower().lstrip("@")
        return f"vibe-trade-tweets-{normalized_username}"

    def _tweet_to_message(self, tweet: Tweet) -> dict:
        """Convert tweet to Pub/Sub message format.

        Args:
            tweet: Tweet data

        Returns:
            Message dictionary
        """
        return {
            "tweet_id": tweet.tweet_id,
            "user_id": tweet.user_id,
            "username": tweet.username,
            "text": tweet.text,
            "timestamp": tweet.timestamp.isoformat(),
            "url": tweet.url,
            "source": tweet.source,
            "retweet_count": tweet.retweet_count,
            "reply_count": tweet.reply_count,
            "like_count": tweet.like_count,
            "quote_count": tweet.quote_count,
            "view_count": tweet.view_count,
            "lang": tweet.lang,
            "bookmark_count": tweet.bookmark_count,
            "is_reply": tweet.is_reply,
            "in_reply_to_id": tweet.in_reply_to_id,
            "conversation_id": tweet.conversation_id,
            "in_reply_to_user_id": tweet.in_reply_to_user_id,
            "in_reply_to_username": tweet.in_reply_to_username,
            "entities": tweet.entities,
            "quoted_tweet": tweet.quoted_tweet,
            "retweeted_tweet": tweet.retweeted_tweet,
            "is_limited_reply": tweet.is_limited_reply,
        }

    def publish_tweet(self, tweet: Tweet) -> str | None:
        """Publish a tweet to Pub/Sub.

        Args:
            tweet: Tweet data to publish

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            topic_name = self._get_tweet_topic_name(tweet.username)
            topic_path = self.publisher.topic_path(self.project_id, topic_name)

            message_data = self._tweet_to_message(tweet)
            message_json = json.dumps(message_data)

            future = self.publisher.publish(
                topic_path,
                message_json.encode("utf-8"),
                ordering_key=tweet.username.lower(),
            )

            message_id = future.result()
            logger.info(
                f"📤 Published tweet to {topic_name}: @{tweet.username} "
                f"({tweet.tweet_id}) (message_id: {message_id})"
            )
            return message_id

        except Exception as e:
            logger.error(f"Failed to publish tweet from @{tweet.username}: {e}", exc_info=True)
            return None

    def publish_tweets(self, tweets_by_user: dict[str, list[Tweet]]) -> dict[str, int]:
        """Publish multiple tweets grouped by user.

        Args:
            tweets_by_user: Dictionary mapping username to list of tweets

        Returns:
            Dictionary mapping username to count of published tweets
        """
        results = {}
        for username, tweets in tweets_by_user.items():
            published = 0
            for tweet in tweets:
                message_id = self.publish_tweet(tweet)
                if message_id:
                    published += 1
            results[username] = published
        return results
