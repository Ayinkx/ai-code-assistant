"""Database models.

Each model is imported here so that ``flask db migrate`` (via Flask-Migrate)
can discover every table in the application.
"""

from app.models.conversation import Conversation
from app.models.github_account import GithubAccount
from app.models.message import Message
from app.models.prompt import Prompt
from app.models.user import User

__all__ = ["Conversation", "GithubAccount", "Message", "Prompt", "User"]
