from typing import List, Optional
import logging
import os
import subprocess

logger = logging.getLogger("GitManager")

class GitManager:
    """
    Wrapper for Git CLI commands, used by agents to manage branches and conflicts.
    """
    def __init__(self, root_path: str = "."):
        self.root_path = os.path.abspath(root_path)

    def _run_git(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.root_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: git {' '.join(args)}\nError: {e.stderr}")
            raise Exception(f"Git Error: {e.stderr.strip()}")

    def get_current_branch(self) -> str:
        return self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])

    def create_branch(self, branch_name: str, base: str = "HEAD"):
        return self._run_git(["checkout", "-b", branch_name, base])

    def commit(self, message: str, all_files: bool = True):
        if all_files:
            self._run_git(["add", "-A"])
        return self._run_git(["commit", "-m", message])

    def merge(self, branch_name: str) -> str:
        try:
            return self._run_git(["merge", branch_name])
        except Exception as e:
            if "CONFLICT" in str(e):
                return "CONFLICT"
            raise e

    def get_conflicts(self) -> List[str]:
        output = self._run_git(["diff", "--name-only", "--diff-filter=U"])
        return output.splitlines() if output else []

    def get_file_content_with_conflicts(self, filepath: str) -> str:
        path = os.path.join(self.root_path, filepath)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def resolve_file(self, filepath: str, resolved_content: str):
        path = os.path.join(self.root_path, filepath)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(resolved_content)
        self._run_git(["add", filepath])

    def abort_merge(self):
        return self._run_git(["merge", "--abort"])

    def push(self, remote: str = "origin", branch: Optional[str] = None):
        if not branch:
            branch = self.get_current_branch()
        return self._run_git(["push", remote, branch])

    def fetch(self, remote: str = "origin"):
        return self._run_git(["fetch", remote])
