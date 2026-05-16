#!/usr/bin/env python3
"""Generate CHANGELOG.md from git commits using conventional commits."""

import subprocess
import re
import sys
from datetime import datetime


def get_commits(since_tag=None):
    cmd = ["git", "log", "--pretty=format:%H|%ad|%s", "--date=short"]
    if since_tag:
        cmd.append(f"{since_tag}..HEAD")
    result = subprocess.run(cmd, capture_output=True, text=True)
    commits = []
    for line in result.stdout.strip().split("\n"):
        if "|" not in line:
            continue
        hash_, date, msg = line.split("|", 2)
        commits.append({"hash": hash_, "date": date, "message": msg})
    return commits


def categorize(msg):
    if msg.startswith("feat"):
        return "Features"
    if msg.startswith("fix"):
        return "Bug Fixes"
    if msg.startswith("docs"):
        return "Documentation"
    if msg.startswith("refactor"):
        return "Refactoring"
    if msg.startswith("test"):
        return "Tests"
    if msg.startswith("chore"):
        return "Chores"
    return "Other"


def generate():
    commits = get_commits()
    groups = {}
    for c in commits:
        cat = categorize(c["message"])
        groups.setdefault(cat, []).append(c)

    lines = ["# Changelog\n", f"Generated: {datetime.utcnow().isoformat()}Z\n"]
    for cat in ["Features", "Bug Fixes", "Refactoring", "Tests", "Documentation", "Chores", "Other"]:
        if cat not in groups:
            continue
        lines.append(f"\n## {cat}\n")
        for c in groups[cat]:
            short = c["hash"][:7]
            lines.append(f"- {c['date']} `{short}` {c['message']}\n")

    with open("CHANGELOG_AUTO.md", "w") as f:
        f.writelines(lines)
    print("Wrote CHANGELOG_AUTO.md")


if __name__ == "__main__":
    generate()
