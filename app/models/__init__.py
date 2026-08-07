"""Database models.

Each model is imported here so that ``flask db migrate`` (via Flask-Migrate)
can discover every table in the application.
"""

from app.models.conversation import Conversation
from app.models.github_account import GithubAccount
from app.models.message import Message
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.models.project_message import ProjectMessage
from app.models.prompt import Prompt
from app.models.user import User
from app.models.workspace import Workspace

__all__ = [
    "Conversation",
    "GithubAccount",
    "Message",
    "Project",
    "ProjectFile",
    "ProjectMessage",
    "Prompt",
    "User",
    "Workspace",
]
