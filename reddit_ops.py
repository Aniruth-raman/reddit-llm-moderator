"""Reddit operations using PRAW - handles fetching, approving, removing posts/comments.
Follows Single Responsibility Principle with clear separation of concerns."""
import praw
from abc import ABC, abstractmethod


class RedditOperations(ABC):
    """Abstract interface for Reddit operations following Interface Segregation Principle."""
    
    @abstractmethod
    def fetch_modqueue_items(self, subreddit_name, limit=10):
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
        subreddit = self.reddit.subreddit(subreddit_name)
        return list(subreddit.mod.modqueue(limit=limit))
    
    def approve_item(self, item):
        """Approve a Reddit submission or comment."""
        item.mod.approve()
    
    def remove_item(self, item, reason="Rule violation"):
        """Remove a Reddit submission or comment."""
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
    subreddit = reddit.subreddit(subreddit_name)
    return list(subreddit.mod.modqueue(limit=limit))

def approve_item(item):
    """Approve a Reddit submission or comment."""
    item.mod.approve()

def remove_item(item, reason="Rule violation"):
    """Remove a Reddit submission or comment."""
    item.mod.remove(reason=reason)