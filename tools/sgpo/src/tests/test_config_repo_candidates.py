from __future__ import annotations

from pathlib import Path
from unittest import mock

from sgpo import cli


def test_repo_root_candidates_include_worktrees_and_smartgit_repo(tmp_path: Path) -> None:
    tool_cwd = tmp_path / "cwd"
    tool_cwd.mkdir()

    session_repo = tmp_path / "session-repo"
    session_repo.mkdir()

    smartgit_repo = tmp_path / "smartgit-repo"
    (smartgit_repo / "po").mkdir(parents=True)

    props_path = tmp_path / "smartgit.properties"
    props_path.write_text(
        f"{cli._SMARTGIT_PROP_KEY_REPO}={smartgit_repo / 'po'}\n",
        encoding="utf-8",
    )

    worktree_repo = tmp_path / "worktree-repo"
    worktree_repo.mkdir()

    def _fake_run_git(args: list[str], cwd: Path) -> str | None:
        if args == ["rev-parse", "--show-toplevel"]:
            return f"{session_repo}\n"
        if args == ["worktree", "list", "--porcelain"]:
            return (
                f"worktree {session_repo}\n"
                "HEAD 0000000\n"
                "branch refs/heads/main\n"
                "\n"
                f"worktree {worktree_repo}\n"
                "HEAD 0000000\n"
                "branch refs/heads/feature\n"
                "\n"
            )
        return None

    with mock.patch("pathlib.Path.cwd", return_value=tool_cwd):
        with mock.patch("sgpo.cli._find_smartgit_properties", return_value=[props_path]):
            with mock.patch("sgpo.cli._run_git", side_effect=_fake_run_git):
                sections = cli._repo_root_choice_sections(str(session_repo), session_repo)

    candidates = [path for _section, items in sections for _label, path in items]
    assert smartgit_repo.resolve() in candidates
    assert worktree_repo.resolve() in candidates
