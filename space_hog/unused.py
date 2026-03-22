"""Unused software detection via layered signal analysis.

Combines 5 signals to detect software you no longer need:
1. Spotlight kMDItemLastUsedDate (GUI apps)
2. Shell history frequency (CLI tools)
3. Homebrew orphans (brew autoremove)
4. Homebrew leaves vs shell history (unused explicit installs)
5. Running process check (is it active right now?)

Each signal contributes to a confidence score: HIGH, MEDIUM, or LOW.
"""

import json
import subprocess
from collections import Counter
from pathlib import Path

from .utils import format_size, get_dir_size, Colors

DIM = '\033[2m'


def _get_shell_history_commands(max_entries: int = 50000) -> Counter:
    """Parse ~/.zsh_history to count command frequencies."""
    history_file = Path.home() / ".zsh_history"
    if not history_file.exists():
        history_file = Path.home() / ".bash_history"
    if not history_file.exists():
        return Counter()

    commands = Counter()
    try:
        with open(history_file, "rb") as f:
            for line in f.readlines()[-max_entries:]:
                try:
                    text = line.decode("utf-8", errors="ignore").strip()
                    # zsh extended history format: : timestamp:0;command
                    if text.startswith(":"):
                        text = text.split(";", 1)[-1] if ";" in text else text
                    # Extract first word (the command)
                    cmd = text.split()[0] if text else ""
                    # Strip paths
                    cmd = cmd.rsplit("/", 1)[-1]
                    if cmd and not cmd.startswith("#"):
                        commands[cmd] += 1
                except (IndexError, UnicodeDecodeError):
                    continue
    except OSError:
        pass

    return commands


# Core tools that are always needed even if not in shell history
# (often invoked by other tools, IDEs, or agents — not typed directly)
CORE_TOOLS = {
    "git", "gh", "curl", "wget", "ssh", "python@3.12", "python@3.11",
    "python@3.10", "python@3.13", "node", "openssl", "ca-certificates",
    "cmake", "pkg-config", "readline", "sqlite", "xz", "zlib",
    "libffi", "gettext", "pcre2", "libyaml",
}

# Profile tags → brew formulas that tag implies are in active use
# If you're tagged "rust-dev", rust/cargo aren't unused — even if not in shell history
TAG_PROTECTED_TOOLS = {
    "python-dev": {"python@3.10", "python@3.11", "python@3.12", "python@3.13", "pyenv", "pipx"},
    "js-dev": {"node", "yarn", "pnpm", "bun", "deno", "typescript"},
    "rust-dev": {"rust", "rustup"},
    "go-dev": {"go", "gopls"},
    "ios-dev": {"cocoapods", "swiftlint", "swiftformat", "fastlane"},
    "docker-user": {"docker", "docker-machine", "docker-compose", "docker-buildx", "colima"},
    "infra-ops": {"terraform", "awscli", "kubectl", "kubernetes-cli", "helm", "pulumi"},
    "paas-user": {"railway", "supabase", "flyctl"},
    "ai-agent-user": {"ollama"},  # local LLM tools are expected for AI agent users
}

# Formula names that differ from the commands they provide
BREW_COMMAND_MAP = {
    "rust": ["rustc", "cargo", "rustup"],
    "go": ["go", "gofmt"],
    "python@3.10": ["python3.10"],
    "python@3.11": ["python3.11"],
    "python@3.12": ["python3.12", "python3"],
    "python@3.13": ["python3.13"],
    "node": ["node", "npm", "npx"],
    "postgresql@14": ["psql", "pg_dump", "postgres"],
    "postgresql@16": ["psql", "pg_dump", "postgres"],
    "awscli": ["aws"],
    "gh": ["gh"],
    "git": ["git"],
    "ripgrep": ["rg"],
    "fd": ["fd"],
    "bat": ["bat"],
    "the_silver_searcher": ["ag"],
    "kubernetes-cli": ["kubectl"],
}


def _brew_commands(formula_name: str) -> list[str]:
    """Return likely command names for a brew formula."""
    if formula_name in BREW_COMMAND_MAP:
        return BREW_COMMAND_MAP[formula_name]
    # Default: the formula name itself, plus check bin dir
    commands = [formula_name]
    for prefix in ["/opt/homebrew/Cellar", "/usr/local/Cellar"]:
        bin_dir = Path(prefix) / formula_name
        if bin_dir.exists():
            # Find the versioned bin dir
            for version_dir in bin_dir.iterdir():
                actual_bin = version_dir / "bin"
                if actual_bin.is_dir():
                    commands.extend(f.name for f in actual_bin.iterdir() if f.is_file())
                    break
    return commands


def _get_brew_leaves() -> list[dict]:
    """Get explicitly installed Homebrew packages with sizes."""
    try:
        out = subprocess.run(
            ["brew", "leaves"],
            capture_output=True, text=True, timeout=15,
        )
        if out.returncode != 0:
            return []

        leaves = []
        for name in out.stdout.strip().split("\n"):
            name = name.strip()
            if not name:
                continue

            # Get install size
            try:
                info_out = subprocess.run(
                    ["brew", "info", "--json=v2", name],
                    capture_output=True, text=True, timeout=10,
                )
                if info_out.returncode == 0:
                    data = json.loads(info_out.stdout)
                    formulae = data.get("formulae", [])
                    if formulae:
                        installed = formulae[0].get("installed", [{}])
                        _ = installed[0].get("installed_as_dependency", False)
                        # Get cellar path for size
                        cellar_path = Path(f"/opt/homebrew/Cellar/{name}")
                        if not cellar_path.exists():
                            cellar_path = Path(f"/usr/local/Cellar/{name}")
                        dir_size = get_dir_size(cellar_path) if cellar_path.exists() else 0
                        leaves.append({
                            "name": name,
                            "size_bytes": dir_size,
                            "type": "brew",
                        })
            except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
                leaves.append({"name": name, "size_bytes": 0, "type": "brew"})

        return leaves
    except (subprocess.TimeoutExpired, OSError):
        return []


def _get_brew_orphans() -> list[dict]:
    """Get orphaned Homebrew dependencies (safe to remove)."""
    try:
        out = subprocess.run(
            ["brew", "autoremove", "--dry-run"],
            capture_output=True, text=True, timeout=30,
        )
        orphans = []
        for line in out.stdout.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("=") and not line.startswith("Would"):
                name = line.strip()
                cellar_path = Path(f"/opt/homebrew/Cellar/{name}")
                if not cellar_path.exists():
                    cellar_path = Path(f"/usr/local/Cellar/{name}")
                size = get_dir_size(cellar_path) if cellar_path.exists() else 0
                orphans.append({
                    "name": name,
                    "size_bytes": size,
                    "type": "brew_orphan",
                    "confidence": "HIGH",
                    "risk_score": 1,
                    "reason": "Orphaned dependency — parent package was uninstalled",
                    "command": f"brew autoremove",
                })
        return orphans
    except (subprocess.TimeoutExpired, OSError):
        return []


def _get_running_processes() -> set:
    """Get set of currently running process names."""
    try:
        out = subprocess.run(
            ["ps", "-eo", "comm="],
            capture_output=True, text=True, timeout=5,
        )
        return {line.rsplit("/", 1)[-1].strip() for line in out.stdout.split("\n") if line.strip()}
    except (subprocess.TimeoutExpired, OSError):
        return set()


def _get_profile_protected_tools() -> set[str]:
    """Get brew formulas protected by the user's profile tags."""
    from .profile import get_tags
    tags = get_tags()
    protected = set()
    for tag, tools in TAG_PROTECTED_TOOLS.items():
        if tag in tags:
            protected.update(tools)
    return protected


def detect_unused_software(min_days: int = 90) -> dict:
    """Detect unused software using layered signal analysis.

    Loads the shared Eidos Mac profile to avoid flagging tools
    that match the user's developer profile (e.g. rust for a rust-dev).

    Returns structured data for agent consumption:
    {
        "unused_apps": [...],
        "unused_brew": [...],
        "brew_orphans": [...],
        "profile_used": bool,
        "summary": { "total_reclaimable": int, "item_count": int }
    }
    """
    history = _get_shell_history_commands()
    running = _get_running_processes()
    profile_protected = _get_profile_protected_tools()

    results = {
        "unused_apps": [],
        "unused_brew": [],
        "brew_orphans": [],
        "profile_used": len(profile_protected) > 0,
        "profile_protected_count": len(profile_protected),
        "summary": {"total_reclaimable": 0, "item_count": 0},
    }

    # --- GUI Apps via Spotlight ---
    try:
        out = subprocess.run(
            ["mdfind", "-onlyin", "/Applications",
             f"kMDItemLastUsedDate < $time.today(-{min_days * 86400})"],
            capture_output=True, text=True, timeout=15,
        )
        for path_str in out.stdout.strip().split("\n"):
            path_str = path_str.strip()
            if not path_str or not path_str.endswith(".app"):
                continue
            app_path = Path(path_str)
            if not app_path.exists():
                continue

            name = app_path.stem
            size = get_dir_size(app_path)

            # Get actual last used date
            try:
                mdls_out = subprocess.run(
                    ["mdls", "-name", "kMDItemLastUsedDate", "-raw", str(app_path)],
                    capture_output=True, text=True, timeout=5,
                )
                last_used = mdls_out.stdout.strip()
                if last_used == "(null)":
                    last_used = "never"
            except (subprocess.TimeoutExpired, OSError):
                last_used = "unknown"

            # Confidence: check if running
            is_running = name.lower() in {p.lower() for p in running}

            if is_running:
                confidence = "LOW"
            elif last_used == "never":
                confidence = "HIGH"
            else:
                confidence = "MEDIUM"

            results["unused_apps"].append({
                "name": name,
                "path": str(app_path),
                "size_bytes": size,
                "last_used": last_used,
                "is_running": is_running,
                "confidence": confidence,
                "risk_score": 2,
                "command": f"open '{app_path}' # verify before removing",
            })
    except (subprocess.TimeoutExpired, OSError):
        pass

    # --- Brew leaves vs shell history ---
    brew_leaves = _get_brew_leaves()
    for pkg in brew_leaves:
        name = pkg["name"]
        if name in CORE_TOOLS:
            continue  # never flag core infrastructure
        if name in profile_protected:
            continue  # matches user's developer profile

        # Check all commands this formula provides
        commands = _brew_commands(name)
        used_count = sum(history.get(cmd, 0) for cmd in commands)
        is_running = any(cmd in running for cmd in commands)

        if used_count == 0 and not is_running:
            confidence = "HIGH"
        elif used_count < 3:
            confidence = "MEDIUM"
        else:
            continue  # actively used

        results["unused_brew"].append({
            "name": name,
            "size_bytes": pkg["size_bytes"],
            "history_count": used_count,
            "is_running": is_running,
            "confidence": confidence,
            "risk_score": 2,
            "reason": f"Never in shell history" if used_count == 0 else f"Used only {used_count} times",
            "command": f"brew uninstall {name}",
        })

    # --- Brew orphans ---
    results["brew_orphans"] = _get_brew_orphans()

    # --- Summary ---
    all_items = results["unused_apps"] + results["unused_brew"] + results["brew_orphans"]
    results["summary"]["total_reclaimable"] = sum(i["size_bytes"] for i in all_items)
    results["summary"]["item_count"] = len(all_items)

    return results


def print_unused_report(min_days: int = 90):
    """Print unused software report to terminal."""
    c = Colors
    data = detect_unused_software(min_days=min_days)

    from .profile import get_user_type

    print(f"\n  {c.BOLD}UNUSED SOFTWARE DETECTION{c.RESET}")
    print(f"  {'=' * 50}")

    user_type = get_user_type()
    if data["profile_used"]:
        print(f"  {DIM}Profile: {user_type} — {data['profile_protected_count']} tools protected by profile{c.RESET}")
    else:
        print(f"  {c.YELLOW}No profile found — run `aad profile` first for smarter detection{c.RESET}")

    if data["brew_orphans"]:
        print(f"\n  {c.GREEN}BREW ORPHANS (safe to remove){c.RESET}")
        total = sum(o["size_bytes"] for o in data["brew_orphans"])
        names = [o["name"] for o in data["brew_orphans"]]
        print(f"    {len(names)} orphaned dependencies: {format_size(total)}")
        if len(names) <= 10:
            print(f"    {', '.join(names)}")
        else:
            print(f"    {', '.join(names[:10])}...")
        print(f"    → brew autoremove")

    if data["unused_apps"]:
        print(f"\n  {c.YELLOW}UNUSED APPS (not opened in {min_days}+ days){c.RESET}")
        for app in sorted(data["unused_apps"], key=lambda a: a["size_bytes"], reverse=True)[:15]:
            conf = app["confidence"]
            conf_color = c.GREEN if conf == "HIGH" else c.YELLOW if conf == "MEDIUM" else DIM
            print(f"    {conf_color}[{conf}]{c.RESET} {app['name']}"
                  f"  {DIM}{format_size(app['size_bytes'])}"
                  f"  last used: {app['last_used'][:10] if app['last_used'] != 'never' else 'never'}{c.RESET}")

    if data["unused_brew"]:
        print(f"\n  {c.YELLOW}UNUSED BREW PACKAGES (not in shell history){c.RESET}")
        for pkg in sorted(data["unused_brew"], key=lambda p: p["size_bytes"], reverse=True)[:15]:
            conf = pkg["confidence"]
            conf_color = c.GREEN if conf == "HIGH" else c.YELLOW
            reason = f"never used" if pkg["history_count"] == 0 else f"used {pkg['history_count']}x"
            print(f"    {conf_color}[{conf}]{c.RESET} {pkg['name']}"
                  f"  {DIM}{format_size(pkg['size_bytes'])}  ({reason}){c.RESET}")

    total = data["summary"]["total_reclaimable"]
    count = data["summary"]["item_count"]
    if total > 0:
        print(f"\n  {c.BOLD}Total reclaimable: {format_size(total)} across {count} items{c.RESET}")
    else:
        print(f"\n  {c.GREEN}No unused software detected.{c.RESET}")
