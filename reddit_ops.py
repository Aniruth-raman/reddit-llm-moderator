"""Reddit operations using PRAW - handles fetching, approving, removing posts/comments."""
import praw

def create_reddit_client(config):
    """Create authenticated Reddit client."""
    return praw.Reddit(
        client_id=config['reddit']['client_id'],
        client_secret=config['reddit']['client_secret'],
        username=config['reddit']['username'],
        password=config['reddit']['password'],
        user_agent=config['reddit']['user_agent']
    )

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