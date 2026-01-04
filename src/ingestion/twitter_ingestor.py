"""Twitter tweet ingestion service."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from ..models.tweet import Tweet
from ..sources.twitter import TwitterAPIAdapter

# Import shared repository from vibe-trade-shared
try:
    from vibe_trade_shared.db.twitter_user_repository import TwitterUserRepository
except ImportError:
    # Fallback if not installed
    TwitterUserRepository = None

logger = logging.getLogger(__name__)


class TwitterIngestor:
    """Real-time Twitter tweet ingestor that polls every minute."""

    def __init__(
        self,
        twitter_adapter: TwitterAPIAdapter,
        user_repository: TwitterUserRepository,
    ):
        """Initialize Twitter ingestor.

        Args:
            twitter_adapter: Twitter API adapter
            user_repository: Repository for monitored users (from vibe-trade-shared)
        """
        self.adapter = twitter_adapter
        self.repository = user_repository
        # Track last fetch time per user to avoid duplicates
        self.last_fetch_times: Dict[str, datetime] = {}

    def fetch_new_tweets_for_user(self, user_data: dict) -> List[Tweet]:
        """Fetch new tweets for a user since last fetch.

        Args:
            user_data: User document from Firestore with 'username' and optionally 'userId'

        Returns:
            List of new tweets
        """
        username = user_data.get("username", "")
        user_id = user_data.get("userId")

        if not username:
            logger.warning(f"User data missing username: {user_data}")
            return []

        # Get last fetch time (default to 2 minutes ago to catch any missed tweets)
        last_fetch = self.last_fetch_times.get(username)
        if not last_fetch:
            # First fetch: get tweets from last 2 minutes
            since_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        else:
            since_time = last_fetch

        try:
            tweets = self.adapter.get_new_tweets_since(
                username=username,
                user_id=user_id,
                since_timestamp=since_time,
                include_replies=False,  # You can make this configurable
            )

            # Update last fetch time
            self.last_fetch_times[username] = datetime.now(timezone.utc)

            logger.info(
                f"✅ Fetched {len(tweets)} new tweets for @{username} "
                f"(since {since_time})"
            )

            return tweets

        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}", exc_info=True)
            return []

    def fetch_all_users(self) -> Dict[str, List[Tweet]]:
        """Fetch new tweets for all monitored users.

        Returns:
            Dictionary mapping username to list of tweets
        """
        users = self.repository.get_all_active_users()
        logger.info(f"📱 Fetching tweets for {len(users)} monitored users...")

        results = {}
        for user_data in users:
            username = user_data.get("username", "")
            if not username:
                continue

            tweets = self.fetch_new_tweets_for_user(user_data)
            if tweets:
                results[username] = tweets

        return results

