# agents/git/git_client.py

import asyncio
import logging
import os
import re
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union


class GitClient:
    """
    Git client for version control operations.
    """

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self.logger = logging.getLogger("agent.git")

    async def init_repo(self) -> bool:
        """
        Initialize a new Git repository if one doesn't exist.
        """
        if os.path.exists(os.path.join(self.repo_path, ".git")):
            self.logger.info(f"Git repository already exists at {self.repo_path}")
            return True

        try:
            result = await self._run_git_command("init")
            self.logger.info(f"Initialized Git repository at {self.repo_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize Git repository: {str(e)}")
            return False

    async def commit_changes(
        self,
        files: List[str],
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Optional[str]:
        """
        Commit changes to the repository.
        Returns the commit hash if successful, None otherwise.
        """
        try:
            # Add files to staging
            for file_path in files:
                await self._run_git_command("add", file_path)

            # Set author if provided
            env = os.environ.copy()
            if author_name and author_email:
                env["GIT_AUTHOR_NAME"] = author_name
                env["GIT_AUTHOR_EMAIL"] = author_email
                env["GIT_COMMITTER_NAME"] = author_name
                env["GIT_COMMITTER_EMAIL"] = author_email

            # Commit changes
            result = await self._run_git_command("commit", "-m", message, env=env)

            # Extract commit hash
            commit_hash = await self.get_last_commit_hash()

            self.logger.info(f"Committed changes with hash {commit_hash}")
            return commit_hash

        except Exception as e:
            self.logger.error(f"Failed to commit changes: {str(e)}")
            return None

    async def create_branch(self, branch_name: str) -> bool:
        """
        Create a new branch.
        """
        try:
            await self._run_git_command("checkout", "-b", branch_name)
            self.logger.info(f"Created and switched to branch {branch_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create branch {branch_name}: {str(e)}")
            return False

    async def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to an existing branch.
        """
        try:
            await self._run_git_command("checkout", branch_name)
            self.logger.info(f"Switched to branch {branch_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch to branch {branch_name}: {str(e)}")
            return False

    async def get_current_branch(self) -> Optional[str]:
        """
        Get the name of the current branch.
        """
        try:
            result = await self._run_git_command("branch", "--show-current")
            return result.strip()
        except Exception as e:
            self.logger.error(f"Failed to get current branch: {str(e)}")
            return None

    async def get_last_commit_hash(self) -> Optional[str]:
        """
        Get the hash of the last commit.
        """
        try:
            result = await self._run_git_command("rev-parse", "HEAD")
            return result.strip()
        except Exception as e:
            self.logger.error(f"Failed to get last commit hash: {str(e)}")
            return None

    async def get_file_history(
        self, file_path: str, max_commits: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get the commit history for a specific file.
        """
        try:
            result = await self._run_git_command(
                "log",
                f"-{max_commits}",
                "--pretty=format:%H|%an|%ae|%ad|%s",
                "--",
                file_path,
            )

            commits = []
            for line in result.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) >= 5:
                    commits.append(
                        {
                            "hash": parts[0],
                            "author_name": parts[1],
                            "author_email": parts[2],
                            "date": parts[3],
                            "message": parts[4],
                        }
                    )

            return commits

        except Exception as e:
            self.logger.error(f"Failed to get file history for {file_path}: {str(e)}")
            return []

    async def _run_git_command(self, *args, env=None) -> str:
        """
        Run a Git command and return the output.
        """
        cmd = ["git"]
        cmd.extend(args)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.repo_path,
            env=env,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Git command failed: {stderr.decode('utf-8')}")

        return stdout.decode("utf-8")
