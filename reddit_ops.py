"""Reddit operations using PRAW - handles fetching, approving, removing posts/comments.
Follows Single Responsibility Principle with clear separation of concerns."""
import logging
import praw
from abc import ABC, abstractmethod

# Configure logging
logger = logging.getLogger(__name__)


class RedditOperations(ABC):
    """Abstract interface for Reddit operations following Interface Segregation Principle."""
    
    @abstractmethod
    def fetch_modqueue_items(self, subreddit_name, limit=17):
        """Fetch items from moderation queue."""
        pass
    
    @abstractmethod
    def approve_item(self, item):
        """Approve a Reddit submission or comment."""
        pass
    
    @abstractmethod
    def remove_item(self, item, reason="Rule violation"):
        """Remove a Reddit submission or comment."""
        pass


class PrawRedditOperations(RedditOperations):
    """PRAW implementation of Reddit operations."""
    
    def __init__(self, reddit_client):
        self.reddit = reddit_client
    
    def fetch_modqueue_items(self, subreddit_name, limit=10):
        """Fetch items from moderation queue."""
        logger.debug(f"Fetching modqueue items from r/{subreddit_name} (limit={limit})")
        subreddit = self.reddit.subreddit(subreddit_name)
        items = list(subreddit.mod.modqueue(limit=limit))
        logger.debug(f"Found {len(items)} items in modqueue")
        return items
    
    def approve_item(self, item):
        """Approve a Reddit submission or comment."""
        logger.debug(f"Approving item: {getattr(item, 'id', 'unknown')}")
        item.mod.approve()
    
    def remove_item(self, item, reason="Rule violation"):
        """Remove a Reddit submission or comment."""
        logger.debug(f"Removing item: {getattr(item, 'id', 'unknown')} with reason: {reason}")
        item.mod.remove(reason=reason)


class RedditClientFactory:
    """Factory for creating Reddit clients following Factory Pattern."""
    
    @staticmethod
    def create_reddit_client(config):
        """Create authenticated Reddit client."""
        return praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            username=config['reddit']['username'],
            password=config['reddit']['password'],
            user_agent=config['reddit']['user_agent']
        )


# Convenience functions for backward compatibility and simpler usage
def create_reddit_client(config):
    """Create authenticated Reddit client."""
    return RedditClientFactory.create_reddit_client(config)

def get_reddit_operations(config):
    """Get Reddit operations instance with proper dependency injection."""
    client = create_reddit_client(config)
    return PrawRedditOperations(client)

def fetch_modqueue_items(reddit, subreddit_name, limit=10):
    """Fetch items from moderation queue."""
    logger.debug(f"Fetching modqueue items from r/{subreddit_name} (limit={limit})")
    subreddit = reddit.subreddit(subreddit_name)
    items = list(subreddit.mod.modqueue(limit=limit))
    logger.debug(f"Found {len(items)} items in modqueue")
    return items

def approve_item(item):
    """Approve a Reddit submission or comment."""
    logger.debug(f"Approving item: {getattr(item, 'id', 'unknown')}")
    item.mod.approve()

def remove_item(item, reason="Rule violation"):
    """Remove a Reddit submission or comment."""
    logger.debug(f"Removing item: {getattr(item, 'id', 'unknown')} with reason: {reason}")
    item.mod.remove(reason=reason)