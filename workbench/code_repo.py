"""Optional Git repository for custom WoltLab packages and styles per project."""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from host_system import detect_host

FORBIDDEN_NAME_RE = re.compile(
    r"(^|/)\.env($|\.)|(^|/)config\.inc\.php$|\.(pem|key|p12|pfx)$|(^|/)(site|data|tls|snapshots|exports|secrets)(/|$)",
    re.I,
)
DEFAULT_BRANCH = "main"
GITHUB_SIGNUP = "https://github.com/signup"


def gh_config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")).expanduser()
    path = base / "wsc-local" / "gh"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    return path


def code_dir(root: Path) -> Path:
    return root / "code"


def worktrees_dir(root: Path) -> Path:
    return root / "worktrees"


def require_git() -> str:
    path = shutil.which("git")
    if not path:
        raise ValueError("Git fehlt. Installiere Git und starte die Workbench erneut.")
    return path


def require_gh() -> str:
    path = shutil.which("gh")
    if not path:
        raise ValueError(
            "GitHub CLI (gh) fehlt. Installationshilfe: https://cli.github.com/ — danach die Workbench erneut öffnen."
        )
    return path


def git(repo: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    command = [require_git(), "-C", str(repo), *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False, env={**os.environ, **(env or {})})
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip() or "Git-Befehl fehlgeschlagen."
        raise RuntimeError(detail)
    return result


def gh(*args: str, check: bool = True, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    command = [require_gh(), *args]
    env = {**os.environ, "GH_CONFIG_DIR": str(gh_config_dir())}
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env, timeout=timeout)
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip() or "GitHub-Befehl fehlgeschlagen."
        raise RuntimeError(detail)
    return result


def write_config(root: Path, cfg: dict[str, Any]) -> None:
    (root / "wsc-local.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def agents_markdown(project: str) -> str:
    return f"""# AGENTS.md – eigener Code für {project}

Dieser Ordner ist das Git-Repository für eigenen WoltLab-Code dieses Projekts.

## Grenzen

- Arbeite nur in diesem Ordner (`packages/`, `styles/` und begleitende Dateien).
- Die laufende Installation liegt unter `../site/` und gehört nicht in Git.
- Keine Geheimnisse, `.env`, Zertifikate, `config.inc.php` oder Datenbankdumps committen.
- Dieses Repository schreibt nicht selbst in die laufende WoltLab-Installation. Pakete und Styles installierst du in WoltLab.

## Parallele Agenten

Für ein zweites Cursor-/VS-Code-Fenster eine Arbeitskopie über die Workbench anlegen (`git worktree`). Nicht denselben Branch in zwei Fenstern bearbeiten.
"""


def readme_markdown(project: str) -> str:
    return f"""# Eigener Code · {project}

Optionaler Arbeitsbereich für eigene WoltLab-Pakete und Styles.

- `packages/` – eigene Pakete
- `styles/` – eigene Styles

Die laufende Suite bleibt außerhalb dieses Repositories. GitHub ist optional und nur für dieses Projekt gedacht.
"""


def code_gitignore() -> str:
    return """# Never version runtime or secrets
.env
*.env
config.inc.php
*.pem
*.key
*.p12
*.pfx
*.sql
site/
data/
tls/
snapshots/
exports/
__pycache__/
.DS_Store
"""


def blocked_paths(paths: list[str]) -> list[str]:
    blocked = []
    for path in paths:
        normalized = path.replace("\\", "/").lstrip("./")
        if not normalized or normalized == ".":
            continue
        if FORBIDDEN_NAME_RE.search(normalized) or normalized.startswith("../"):
            blocked.append(normalized)
    return sorted(set(blocked))


def listed_paths(repo: Path) -> list[str]:
    tracked = git(repo, "ls-files", "-z", check=True).stdout.split("\0")
    staged = git(repo, "diff", "--cached", "--name-only", "-z", check=True).stdout.split("\0")
    unstaged = git(repo, "diff", "--name-only", "-z", check=True).stdout.split("\0")
    # Include ignored files so secrets cannot hide behind .gitignore.
    untracked = git(repo, "ls-files", "--others", "-z", check=True).stdout.split("\0")
    return [item for item in tracked + staged + unstaged + untracked if item]


def assert_safe_tree(repo: Path) -> None:
    paths = listed_paths(repo)
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(repo).as_posix()
        except ValueError:
            continue
        if relative.startswith(".git/"):
            continue
        paths.append(relative)
    blocked = blocked_paths(paths)
    if blocked:
        raise ValueError(
            "Commit und Push wurden gestoppt. Diese Dateien gehören nicht in den eigenen Code:\n- "
            + "\n- ".join(blocked[:20])
        )


def ensure_local_identity(repo: Path) -> None:
    name = git(repo, "config", "--local", "--get", "user.name", check=False).stdout.strip()
    email = git(repo, "config", "--local", "--get", "user.email", check=False).stdout.strip()
    if not name:
        git(repo, "config", "--local", "user.name", "wsc-local")
    if not email:
        git(repo, "config", "--local", "user.email", "wsc-local@localhost")


def expected_repo_name(project: str) -> str:
    return f"wsc-{project}"


def configured_github(cfg: dict[str, Any]) -> dict[str, str] | None:
    value = cfg.get("code_github")
    if not isinstance(value, dict):
        return None
    owner = value.get("owner")
    name = value.get("name")
    url = value.get("url")
    if isinstance(owner, str) and isinstance(name, str) and isinstance(url, str):
        return {"owner": owner, "name": name, "url": url}
    return None


def origin_url(repo: Path) -> str:
    return git(repo, "remote", "get-url", "origin", check=False).stdout.strip()


def normalize_remote(url: str) -> str:
    value = url.strip().removesuffix(".git")
    value = re.sub(r"^git@github\.com:", "https://github.com/", value)
    value = re.sub(r"^ssh://git@github\.com/", "https://github.com/", value)
    return value.rstrip("/")


def assert_managed_origin(repo: Path, cfg: dict[str, Any]) -> dict[str, str]:
    github = configured_github(cfg)
    if not github:
        raise ValueError("Für dieses Projekt ist noch kein von der Workbench verwaltetes GitHub-Repository hinterlegt.")
    remote = origin_url(repo)
    if not remote:
        raise ValueError("Der Git-Remote origin fehlt. Lege zuerst das private GitHub-Repository über die Workbench an.")
    if normalize_remote(remote) != normalize_remote(github["url"]):
        raise ValueError(
            f"origin zeigt auf {remote}, erwartet wird {github['url']}. Die Workbench ändert fremde Remotes nicht."
        )
    return github


def _inside(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except (OSError, ValueError):
        return False
    return True


def list_worktrees(root: Path, repo: Path) -> list[dict[str, str]]:
    base = worktrees_dir(root)
    if not base.is_dir() or not ((repo / ".git").exists() or (repo / ".git").is_file()):
        return []
    items: list[dict[str, str]] = []
    raw = git(repo, "worktree", "list", "--porcelain", check=False).stdout
    current_path = ""
    current_branch = ""

    def remember() -> None:
        nonlocal current_path, current_branch
        if current_path and current_branch:
            path = Path(current_path)
            if _inside(path, base):
                items.append({"branch": current_branch, "path": str(path)})
        current_path, current_branch = "", ""

    for line in raw.splitlines():
        if line.startswith("worktree "):
            remember()
            current_path = line[len("worktree ") :].strip()
        elif line.startswith("branch refs/heads/"):
            current_branch = line[len("branch refs/heads/") :].strip()
        elif line == "":
            remember()
    remember()
    return items


def gh_authenticated() -> bool:
    if not shutil.which("gh"):
        return False
    result = gh("auth", "status", check=False)
    return result.returncode == 0


def code_status(name: str, cfg: dict[str, Any], root: Path) -> dict[str, Any]:
    repo = code_dir(root)
    enabled = (repo / ".git").exists() or (repo / ".git").is_file()
    status: dict[str, Any] = {
        "enabled": enabled,
        "path": str(repo) if enabled else "",
        "branch": "",
        "dirty": False,
        "github": configured_github(cfg),
        "worktrees": [],
        "git_available": bool(shutil.which("git")),
        "gh_available": bool(shutil.which("gh")),
        "gh_authenticated": False,
        "signup_url": GITHUB_SIGNUP,
    }
    if not enabled:
        status["gh_authenticated"] = gh_authenticated() if status["gh_available"] else False
        return status
    try:
        require_git()
        status["branch"] = git(repo, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip() or DEFAULT_BRANCH
        dirty = git(repo, "status", "--porcelain", check=False).stdout.strip()
        status["dirty"] = bool(dirty)
        status["worktrees"] = list_worktrees(root, repo)
        status["gh_authenticated"] = gh_authenticated() if status["gh_available"] else False
    except (OSError, RuntimeError, ValueError) as exc:
        status["error"] = str(exc)
    return status


def init_code(name: str, cfg: dict[str, Any], root: Path) -> str:
    require_git()
    repo = code_dir(root)
    if (repo / ".git").exists() or (repo / ".git").is_file():
        return f"Eigenes Code-Repository ist bereits vorhanden: {repo}"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "packages").mkdir(exist_ok=True)
    (repo / "styles").mkdir(exist_ok=True)
    (repo / "packages" / ".gitkeep").write_text("", encoding="utf-8")
    (repo / "styles" / ".gitkeep").write_text("", encoding="utf-8")
    (repo / ".gitignore").write_text(code_gitignore(), encoding="utf-8")
    (repo / "README.md").write_text(readme_markdown(name), encoding="utf-8")
    (repo / "AGENTS.md").write_text(agents_markdown(name), encoding="utf-8")
    git(repo, "init", "-b", DEFAULT_BRANCH)
    ensure_local_identity(repo)
    git(repo, "add", ".")
    assert_safe_tree(repo)
    git(repo, "commit", "-m", "Initial custom code workspace")
    cfg["code_enabled"] = True
    write_config(root, cfg)
    return (
        f"Eigenes Code-Repository angelegt: {repo}\n"
        "Enthalten: packages/, styles/, README.md, AGENTS.md.\n"
        "Die laufende Installation unter site/ bleibt außerhalb von Git."
    )


def commit_code(name: str, cfg: dict[str, Any], root: Path, message: str) -> str:
    del name, cfg
    require_git()
    repo = code_dir(root)
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise ValueError("Zuerst unter Werkzeuge „Repository anlegen“ ausführen.")
    if not isinstance(message, str) or not message.strip() or "\n" in message or "\r" in message:
        raise ValueError("Bitte eine einzeilige Commit-Nachricht angeben.")
    if len(message.strip()) > 200:
        raise ValueError("Die Commit-Nachricht darf höchstens 200 Zeichen lang sein.")
    ensure_local_identity(repo)
    git(repo, "add", "-A")
    assert_safe_tree(repo)
    pending = git(repo, "status", "--porcelain", check=True).stdout.strip()
    if not pending:
        return "Keine Änderungen zum Committen."
    git(repo, "commit", "-m", message.strip())
    return f"Commit erstellt: {message.strip()}"


def add_worktree(name: str, cfg: dict[str, Any], root: Path, branch: str) -> str:
    del name, cfg
    require_git()
    if not isinstance(branch, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._/-]{0,63}", branch):
        raise ValueError("Branch-Name: Kleinbuchstaben, Zahlen, Punkt, Unterstrich, Slash oder Bindestrich.")
    if branch in {DEFAULT_BRANCH, "master"}:
        raise ValueError(f"Für parallele Agenten einen eigenen Branch wählen, nicht {branch}.")
    repo = code_dir(root)
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise ValueError("Zuerst unter Werkzeuge „Repository anlegen“ ausführen.")
    target = worktrees_dir(root) / branch.replace("/", "-")
    if target.exists():
        raise ValueError(f"Arbeitskopie existiert bereits: {target}")
    worktrees_dir(root).mkdir(parents=True, exist_ok=True)
    existing = git(repo, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    if existing.returncode == 0:
        git(repo, "worktree", "add", str(target), branch)
    else:
        git(repo, "worktree", "add", "-b", branch, str(target))
    opened = ""
    for command in ("cursor", "code"):
        executable = shutil.which(command)
        if executable:
            subprocess.Popen([executable, str(target)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            opened = f"\nIn {command} geöffnet."
            break
    return f"Arbeitskopie bereit: {target}\nBranch: {branch}{opened or chr(10) + 'Pfad zum Öffnen in Cursor/VS Code kopieren.'}"


def terminal_login_command(status: Path, kind: str | None = None) -> list[str]:
    kind = kind or detect_host()["kind"]
    config = gh_config_dir()
    inner = (
        f"export GH_CONFIG_DIR={shlex.quote(str(config))}; "
        "if ! command -v gh >/dev/null 2>&1; then echo 'GitHub CLI (gh) fehlt.' >&2; echo 1 > "
        + shlex.quote(str(status))
        + "; read -r _; exit 1; fi; "
        "printf '\\n' | gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key; "
        f"echo $? > {shlex.quote(str(status))}; "
        "printf '\\nFertig. Dieses Fenster kannst du schließen.\\n'; read -r _ || true"
    )
    command = ["bash", "-lc", inner]
    if kind == "macos":
        line = shlex.join(command)
        return ["osascript", "-e", "tell application \"Terminal\" to do script " + json.dumps(line, ensure_ascii=False), "-e", "tell application \"Terminal\" to activate"]
    if kind == "wsl2":
        distro = os.environ.get("WSL_DISTRO_NAME")
        if not distro:
            raise RuntimeError("Die WSL2-Distribution konnte nicht ermittelt werden.")
        args = ["wsl.exe", "--distribution", distro, "--exec", *command]
        import base64

        expression = "& " + " ".join("'" + value.replace("'", "''") + "'" for value in args)
        launch = (
            "Start-Process powershell.exe -ArgumentList "
            + "'-NoProfile','-EncodedCommand','"
            + base64.b64encode(expression.encode("utf-16le")).decode()
            + "'"
        )
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", launch]
    if kind == "linux":
        for executable, args in (
            ("x-terminal-emulator", ["-e"]),
            ("gnome-terminal", ["--"]),
            ("konsole", ["-e"]),
            ("xfce4-terminal", ["--disable-server", "-x"]),
            ("xterm", ["-e"]),
        ):
            if shutil.which(executable):
                return [executable, *args, *command]
    raise RuntimeError(
        "Kein Systemterminal verfügbar. Im Terminal ausführen: "
        f"GH_CONFIG_DIR={shlex.quote(str(config))} gh auth login -h github.com -p https -w"
    )


def github_login(root: Path | None = None, timeout: float = 3600) -> str:
    del timeout
    require_gh()
    if gh_authenticated():
        return "GitHub-Anmeldung für die Workbench ist bereits vorhanden."
    base = (root or Path(__file__).resolve().parent.parent) / "var" / "github-login"
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    status = base / (uuid.uuid4().hex + ".status")
    descriptor = os.open(status, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        command = terminal_login_command(status)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time

        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            value = status.read_text().strip()
            if value:
                if value != "0":
                    raise RuntimeError(
                        "Die GitHub-Anmeldung wurde nicht abgeschlossen. Folge den Hinweisen im Systemterminal und versuche es erneut."
                    )
                return "GitHub-Anmeldung für die Workbench ist eingerichtet. Fremde gh-Konfigurationen bleiben unberührt."
            if process.poll() not in (None, 0):
                raise RuntimeError(
                    "Das Systemterminal konnte nicht geöffnet werden. Manuell: "
                    f"GH_CONFIG_DIR={shlex.quote(str(gh_config_dir()))} gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key"
                )
            time.sleep(1)
        raise RuntimeError("Die GitHub-Anmeldung meldet keinen Abschluss. Prüfe das Terminal und versuche es erneut.")
    finally:
        status.unlink(missing_ok=True)


def github_create(name: str, cfg: dict[str, Any], root: Path) -> str:
    require_git()
    require_gh()
    if not gh_authenticated():
        raise ValueError("Zuerst unter Werkzeuge bei GitHub anmelden.")
    repo = code_dir(root)
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise ValueError("Zuerst unter Werkzeuge „Repository anlegen“ ausführen.")
    existing = configured_github(cfg)
    if existing:
        assert_managed_origin(repo, cfg)
        return f"GitHub-Repository ist bereits verknüpft: {existing['url']}"
    remote = origin_url(repo)
    if remote:
        raise ValueError(f"origin ist bereits gesetzt ({remote}). Die Workbench übernimmt keine fremden Remotes.")
    repo_name = expected_repo_name(name)
    probe = gh("repo", "view", repo_name, "--json", "name", check=False)
    if probe.returncode == 0:
        raise ValueError(
            f"Das Repository {repo_name} existiert bereits auf GitHub. Die Workbench übernimmt keine fremden Repositorys."
        )
    created = gh(
        "repo",
        "create",
        repo_name,
        "--private",
        "--source",
        str(repo),
        "--remote",
        "origin",
        "--description",
        f"Custom WoltLab code for local project {name}",
    )
    url = origin_url(repo)
    if not url:
        # gh may print the URL even if remote parsing differs across versions.
        match = re.search(r"https://github.com/[^\s]+", created.stdout + created.stderr)
        url = match.group(0).rstrip("/") if match else f"https://github.com/{repo_name}"
    owner = url.rstrip("/").split("/")[-2] if "/" in url.rstrip("/") else ""
    if not owner:
        owner = gh("api", "user", "--jq", ".login").stdout.strip().strip('"')
    if not owner:
        raise RuntimeError("GitHub-Benutzer konnte nicht ermittelt werden.")
    full = f"https://github.com/{owner}/{repo_name}"
    cfg["code_github"] = {"owner": owner, "name": repo_name, "url": full}
    write_config(root, cfg)
    return (
        f"Privates GitHub-Repository angelegt und als origin gesetzt: {full}\n"
        "Noch nichts gepusht. Committe Änderungen und bestätige danach den Push."
    )


def push_code(name: str, cfg: dict[str, Any], root: Path, confirmed: bool = False) -> str:
    del name
    require_git()
    require_gh()
    if not confirmed:
        raise ValueError("Push braucht eine ausdrückliche Bestätigung (--yes).")
    repo = code_dir(root)
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise ValueError("Zuerst unter Werkzeuge „Repository anlegen“ ausführen.")
    github = assert_managed_origin(repo, cfg)
    assert_safe_tree(repo)
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() or DEFAULT_BRANCH
    result = git(repo, "push", "-u", "origin", branch)
    return f"Push nach {github['url']} ({branch}) abgeschlossen.\n{(result.stdout + result.stderr).strip()}".strip()


def activity(name: str, cfg: dict[str, Any], root: Path) -> str:
    del name
    require_gh()
    repo = code_dir(root)
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        raise ValueError("Zuerst unter Werkzeuge „Repository anlegen“ ausführen.")
    github = assert_managed_origin(repo, cfg)
    full = f"{github['owner']}/{github['name']}"
    commits = gh(
        "api",
        f"repos/{full}/commits?per_page=5",
        "--jq",
        ".[] | [.sha[0:7], (.commit.author.date // \"\"), (.commit.message | split(\"\\n\")[0])] | @tsv",
        check=False,
    )
    pulls = gh(
        "api",
        f"repos/{full}/pulls?state=all&per_page=5",
        "--jq",
        ".[] | [.number, .state, .title] | @tsv",
        check=False,
    )
    lines = [f"Aktivität für {full}", "", "Commits:"]
    commit_text = commits.stdout.strip()
    if commit_text:
        lines.extend(f"- {line}" for line in commit_text.splitlines())
    else:
        lines.append("- keine")
    lines.extend(["", "Pull Requests:"])
    pull_text = pulls.stdout.strip()
    if pull_text:
        lines.extend(f"- #{line}" for line in pull_text.splitlines())
    else:
        lines.append("- keine")
    return "\n".join(lines)
