"""Dotfile groups: choose the groups for a host and apply them with `mise dot`."""

from __future__ import annotations

import filecmp
import os
import re
from pathlib import Path
from typing import Sequence

from . import system
from .core import die, log, parse_profile_file

# Groups are directories `home/<group>/` declared in the repository's `mise.toml`.
GROUP_ALWAYS = ("core", "prompt")
GROUP_SYSTEMD_EXCLUDED = ("container",)
GROUP_WORK_PROFILES = ("work-machine",)


def dotfile_groups(profile: str, features: Sequence[str] = ()) -> list[str]:
    """Groups a host receives, derived from its profile (and features)."""
    groups = list(GROUP_ALWAYS)
    if profile not in GROUP_SYSTEMD_EXCLUDED:
        groups.append("systemd")
    if profile in GROUP_WORK_PROFILES:
        groups.append("work")
    if "fonts" in features:
        groups.append("fonts")
    if "thunderbird" in features:
        groups.append("thunderbird")
    return groups


def render_local_config(groups: Sequence[str]) -> str:
    names = ", ".join(f'"{g}"' for g in groups)
    return f"[bootstrap]\ndotfile_groups = [{names}]\n"


GITCONFIG_LOCAL_HEADER = """\
# Host-local git config, included near the end of ~/.gitconfig; only the owner rules
# (remote URL -> work/private identity) come after it.
# Created once by `machine setup` from the machine profile and never overwritten — edit freely.
# Put host-only settings here: signingkey/gpg, safe.directory, credential helpers, proxy.
# Per-repo exceptions: `git user-work` / `git user-private`.
"""

CA_INFO_BLOCK = """\
# The user-space Git (mise) ignores /etc/gitconfig and the system CA bundle.
[http]
    sslCAInfo = /etc/ssl/certs/ca-certificates.crt
"""


def render_gitconfig_local(profile: str) -> str:
    """Profile defaults for ~/.gitconfig.local (identity, CA bundle, safe.directory)."""
    if profile == "work-machine":
        name, email = (
            "Ditscher Christian (XC-AS/ESE1)",
            "christian.ditscher@de.bosch.com",
        )
    else:
        name, email = "Christian Ditscher", "chris@ditscher.me"
    text = f"{GITCONFIG_LOCAL_HEADER}\n[user]\n    name = {name}\n    email = {email}\n"
    text += "\n[credential]\n    helper = store\n"
    if profile == "work-machine":
        text += f"\n{CA_INFO_BLOCK}"
        text += "\n[safe]\n    directory = /opt/osd/ansible/osd-ansible-custom\n"
    if profile == "container":
        text += "\n[safe]\n    directory = /workspace\n"
    return text


GITHUB_TOKEN_CONFIG = ".config/git/github-token.gitconfig"


def github_token_variable(profile: str) -> str:
    """On work machines GITHUB_TOKEN is the work token, so private GitHub uses its own."""
    return "GITHUB_PRIVATE_TOKEN" if profile in GROUP_WORK_PROFILES else "GITHUB_TOKEN"


def render_github_token_config(profile: str) -> str:
    return (
        "# Written by `machine` from the host profile on every dotfile apply; do not edit.\n"
        "# Included by ~/.config/git/private.gitconfig after its credential reset.\n"
        '[credential "https://github.com"]\n'
        "    helper = !$HOME/.local/bin/git-credential-env "
        f"{github_token_variable(profile)}\n"
    )


SSH_REMOTE_EXCLUDED = ("work-machine", "container")


def github_ssh_url(url: str) -> str:
    """`https://github.com/<owner>/<repo>[.git]` as SSH URL, else an empty string."""
    match = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?", url.strip()
    )
    return f"git@github.com:{match.group(1)}/{match.group(2)}.git" if match else ""


SWEEP_SKIP_DIRS = {
    ".cache",
    ".git",
    ".nvm",
    ".npm",
    ".docker-cache",
    "node_modules",
    "share",
    ".pyenv",
    ".rustup",
    ".cargo",
}
SWEEP_MAX_DEPTH = 5


def sweep_dangling_links(home: Path, repo: Path) -> list[Path]:
    """Remove dangling symlinks in `home` whose target lay inside the checkout."""
    repo = repo.resolve()
    removed: list[Path] = []
    base_depth = len(home.parts)
    for current, dirs, files in os.walk(home):
        depth = len(Path(current).parts) - base_depth
        dirs[:] = [
            d
            for d in dirs
            if d not in SWEEP_SKIP_DIRS
            and depth < SWEEP_MAX_DEPTH
            and not os.path.islink(os.path.join(current, d))
        ]
        for name in files:
            link = Path(current) / name
            if not link.is_symlink() or link.exists():
                continue
            target = Path(os.path.normpath(Path(current) / os.readlink(link)))
            if target == repo or repo in target.parents:
                link.unlink()
                removed.append(link)
    return removed


def group_targets(
    repo: Path, home: Path, groups: Sequence[str]
) -> list[tuple[Path, Path]]:
    """(source in the checkout, target in `home`) for every file of the given groups."""
    pairs = []
    for group in groups:
        root = repo / "home" / group
        for current, _dirs, files in os.walk(root):
            for name in files:
                source = Path(current) / name
                pairs.append((source, home / source.relative_to(root)))
    return pairs


def clear_conflicting_targets(
    repo: Path, home: Path, groups: Sequence[str]
) -> list[tuple[Path, str]]:
    """Make room for `mise dot apply`, which refuses to overwrite existing files.

    A link pointing elsewhere into the checkout (an old layout) is removed; a regular
    file is deleted when its content equals the repository file, else moved aside to
    `<name>.pre-dotfiles`. Anything else that is
    already the right link, or a link outside the checkout, is left for mise to report.
    """
    repo = repo.resolve()
    changed: list[tuple[Path, str]] = []
    for source, target in group_targets(repo, home, groups):
        if target.is_symlink():
            current = Path(os.path.normpath(target.parent / os.readlink(target)))
            if current != source and (current == repo or repo in current.parents):
                target.unlink()
                changed.append((target, "removed stale link"))
        elif target.is_file():
            if filecmp.cmp(source, target, shallow=False):
                target.unlink()
                changed.append((target, "removed identical file"))
                continue
            backup = target.with_name(target.name + ".pre-dotfiles")
            n = 1
            while backup.exists() or backup.is_symlink():
                n += 1
                backup = target.with_name(f"{target.name}.pre-dotfiles.{n}")
            target.rename(backup)
            changed.append((target, f"moved aside to {backup.name}"))
    return changed


class DotfilesMixin:
    def ensure_gitconfig_local(self, profile: str) -> None:
        """Create ~/.gitconfig.local once; an existing file is only extended on work hosts
        that lack the CA bundle key (the user-space Git ignores the system store)."""
        path = self.home / ".gitconfig.local"
        if not path.exists():
            path.write_text(render_gitconfig_local(profile), encoding="utf-8")
            return
        if profile != "work-machine":
            return
        text = path.read_text(encoding="utf-8")
        if "sslcainfo" not in text.lower():
            path.write_text(
                text.rstrip("\n") + f"\n\n{CA_INFO_BLOCK}", encoding="utf-8"
            )
            log("added http.sslCAInfo to ~/.gitconfig.local")

    def write_dotfile_groups(self, profile: str) -> None:
        """Write the host's group list into the local mise configuration."""
        features = parse_profile_file(self.profile_path)["features"]
        self.ensure_dirs()
        self.mise_local_config.parent.mkdir(parents=True, exist_ok=True)
        self.mise_local_config.write_text(
            render_local_config(dotfile_groups(profile, features)), encoding="utf-8"
        )

    def dotfiles_env(self) -> dict:
        env = dict(os.environ)
        env["MISE_DOTFILES_ROOT"] = str(self.repo)
        return env

    def run_dotfiles_apply(self) -> None:
        if not system.have("mise"):
            die("mise is not installed (run: ./bootstrap)")
        if not self.mise_local_config.is_file():
            die(f"missing {self.mise_local_config} (run: machine setup)")
        profile = str(parse_profile_file(self.profile_path)["profile"] or "home-laptop")
        self.ensure_gitconfig_local(profile)
        self.write_github_token_config(profile)
        features = parse_profile_file(self.profile_path)["features"]
        for target, what in clear_conflicting_targets(
            Path(self.repo), self.home, dotfile_groups(profile, features)
        ):
            log(f"{target}: {what}")
        env = self.dotfiles_env()
        project = Path(self.repo) / "mise.toml"
        system.run(["mise", "trust", str(project)], env=env, check=False, capture=True)
        # --yes: on a terminal mise asks before replacing live targets, even under
        # `machine setup --yes`; conflicting files were already moved aside above.
        system.run(["mise", "dot", "apply", "--prune", "--yes"], env=env, cwd=self.repo)
        for link in sweep_dangling_links(self.home, Path(self.repo)):
            log(f"removed dangling link {link}")
        self.ensure_machine_link()

    def write_github_token_config(self, profile: str) -> None:
        path = self.home / GITHUB_TOKEN_CONFIG
        text = render_github_token_config(profile)
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        log(f"GitHub token for github.com: {github_token_variable(profile)} ({path})")

    def switch_origin_to_ssh(self, profile: str) -> None:
        """Private hosts push with their SSH key: move an https github.com origin to SSH,
        but only when SSH to GitHub authenticates. Work machines keep HTTPS."""
        if profile in SSH_REMOTE_EXCLUDED:
            return
        current = system.run(
            ["git", "-C", str(self.repo), "remote", "get-url", "origin"],
            check=False,
            capture=True,
        )
        ssh_url = (
            github_ssh_url(current.stdout or "") if current.returncode == 0 else ""
        )
        if not ssh_url or not system.have("ssh"):
            return
        probe = system.run(
            [
                "ssh", "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                "-o", "StrictHostKeyChecking=accept-new", "git@github.com",
            ],
            check=False,
            capture=True,
        )  # fmt: skip
        if "successfully authenticated" not in (probe.stderr or "") + (
            probe.stdout or ""
        ):
            log("SSH to GitHub does not authenticate; origin stays on HTTPS")
            return
        system.run(
            ["git", "-C", str(self.repo), "remote", "set-url", "origin", ssh_url]
        )
        log(f"origin now uses SSH: {ssh_url}")

    def ensure_machine_link(self) -> None:
        """~/.local/bin/machine -> the CLI of this checkout (like bootstrap).

        Replaces the copied entry point of the earlier layout, which breaks as
        soon as the checkout no longer has the modules it imports."""
        link = self.home / ".local" / "bin" / "machine"
        target = Path(self.repo) / "machine_cli" / "machine"
        if link.is_symlink() and link.resolve() == target.resolve():
            return
        link.parent.mkdir(parents=True, exist_ok=True)
        tmp = link.with_name(".machine.tmp")
        if tmp.is_symlink() or tmp.exists():
            tmp.unlink()
        tmp.symlink_to(target)
        os.replace(tmp, link)
        log(f"linked {link} to {target}")

    def dotfiles_health_failure(self) -> str:
        """Reason why the group configuration is unusable, or an empty string."""
        if not (system.have("mise") and self.mise_local_config.exists()):
            return ""
        try:
            self.mise_local_config.read_bytes()
        except OSError as exc:
            return f"mise group configuration unreadable: {exc}"
        return ""
