from shared.Moderation import ModerationRule
from shared.utils import logger


class NotificationStrategy:
    """Base class for notification strategies."""

    def notify(self, item, rule: ModerationRule, subreddit) -> None:
        """Send notification for a removed item."""
        pass


class PublicNotificationStrategy(NotificationStrategy):
    """Strategy for public notifications."""

    def notify(self, item, rule: ModerationRule, subreddit) -> None:
        """Send a public notification via comment or removal message."""
        is_submission = hasattr(item, "title")
        response_text = rule.response

        if is_submission:
            item.mod.send_removal_message(response_text, type="public")
        else:
            try:
                item.reply(response_text)
            except Exception as e:
                logger.warning(f"Could not reply to comment: {e}")


class ModmailNotificationStrategy(NotificationStrategy):
    """Strategy for modmail notifications."""

    def notify(self, item, rule: ModerationRule, subreddit) -> None:
        """Send a notification via modmail."""
        is_submission = hasattr(item, "title")
        response_text = rule.response

        try:
            # For both submissions and comments
            author = item.author
            if author:  # Ensure author exists (not deleted)
                # Create subject line
                subject = f"Post Removal from r/{subreddit.display_name}"

                # Compose modmail message
                message_body = f"{response_text}\n\n"

                if is_submission:
                    message_body += f"Your post titled: '{item.title}' was removed."
                else:
                    # For comments, include part of the comment and link to parent
                    message_body += f"Your comment: '{item.body[:100]}...' was removed."

                # Send the modmail
                author.message(subject, message_body, from_subreddit=subreddit)
                logger.info(f"Sent removal reason via modmail to u/{author.name}")
        except Exception as e:
            logger.warning(f"Could not send modmail: {e}")
