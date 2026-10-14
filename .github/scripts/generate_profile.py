#!/usr/bin/env python3
"""Generate monochrome SVG profile assets from GitHub's public API."""

import json
import os
import sys
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.request import Request, urlopen

USERNAME = "B4nJuice"
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
INK = "#242424"
MUTED = "#6b6b6b"
GRID = "#e5e5e5"
ACCENTS = ("#d6d6d6", "#b5b5b5", "#8f8f8f", "#5f5f5f", "#242424")


def api(path):
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "B4nJuice-profile-generator",
        },
    )
    token = os.getenv("GITHUB_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except Exception as error:
        print(f"GitHub API request failed for {path}: {error}", file=sys.stderr)
        raise


def svg(width, height, content):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><style>text{{font-family:-apple-system,'
        f'BlinkMacSystemFont,"Segoe UI",sans-serif}}</style>{content}</svg>\n'
    )


def text(value, x, y, size=14, fill=INK, weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'
    )


def card(width, height, title):
    return (
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" '
        f'fill="none" stroke="{GRID}" stroke-opacity=".7"/>{text(title, 24, 31, 13, MUTED, "600")}'
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as asset:
        asset.write(content)


def logo_name(language):
    return re.sub(r"[^a-z0-9]+", "-", language.lower()).strip("-") or "language"


def make_logo(language, index):
    initials = "".join(part[0] for part in language.split()[:2])[:2] or language[:2]
    content = (
        f'<circle cx="18" cy="18" r="16" fill="{ACCENTS[index % len(ACCENTS)]}"/>'
        f'{text(initials.upper(), 18, 22, 10, "#fff", "700", "middle")}'
    )
    logo_dir = os.path.join(OUT, "logos")
    os.makedirs(logo_dir, exist_ok=True)
    with open(os.path.join(logo_dir, f"{logo_name(language)}.svg"), "w", encoding="utf-8") as asset:
        asset.write(svg(36, 36, content))


def make_stack(languages):
    top = languages.most_common(7)
    total = sum(languages.values()) or 1
    content = card(760, 116, "LANGUAGES IN MY REPOSITORIES")
    for index, (language, amount) in enumerate(top):
        x = 24 + (index % 4) * 184
        y = 48 + (index // 4) * 34
        percent = amount / total * 100
        make_logo(language, index)
        content += f'<image href="logos/{logo_name(language)}.svg" x="{x - 8}" y="{y - 16}" width="36" height="36"/>'
        content += text(f"{language}  {percent:.1f}%", x + 28, y + 6, 11, INK, "600")
    if not top:
        content += text("No language data available yet.", 24, 65, 12, MUTED)
    write("stack.svg", svg(760, 116, content))


def make_stats(user, repos):
    original = [repo for repo in repos if not repo.get("fork")]
    stars = sum(repo.get("stargazers_count", 0) for repo in original)
    followers = user.get("followers", 0)
    commits = sum(repo.get("size", 0) > 0 for repo in original)
    content = card(760, 150, "GITHUB OVERVIEW")
    metrics = (("PUBLIC REPOS", len(original)), ("FOLLOWERS", followers),
               ("TOTAL STARS", stars), ("ACTIVE PROJECTS", commits))
    for index, (label, value) in enumerate(metrics):
        x = 24 + index * 184
        content += text(value, x, 84, 27, INK, "700")
        content += text(label, x, 108, 10, MUTED, "600")
    write("stats.svg", svg(760, 150, content))


def make_languages(repos):
    languages = Counter()
    for repo in repos:
        if repo.get("fork"):
            continue
        for language, amount in (repo.get("languages") or {}).items():
            languages[language] += amount
    top = languages.most_common(5)
    total = sum(languages.values()) or 1
    content = card(760, 150, "LANGUAGE DISTRIBUTION")
    x = 24
    for index, (language, amount) in enumerate(top):
        width = max(8, round(712 * amount / total))
        content += f'<rect x="{x}" y="54" width="{width}" height="10" fill="{ACCENTS[index]}"/>'
        x += width
    x = 24
    for index, (language, amount) in enumerate(top):
        percent = amount / total * 100
        content += f'<circle cx="{x + 4}" cy="91" r="4" fill="{ACCENTS[index]}"/>'
        content += text(f"{language}  {percent:.1f}%", x + 14, 95, 11, MUTED)
        x += 145
    if not top:
        content += text("No language data available yet.", 24, 85, 12, MUTED)
    write("languages.svg", svg(760, 150, content))


def make_activity(events):
    today = datetime.now(timezone.utc).date()
    counts = Counter()
    for event in events:
        if event.get("type") not in ("PushEvent", "PullRequestEvent", "IssuesEvent"):
            continue
        try:
            date = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00")).date()
            counts[date] += 1
        except (KeyError, ValueError):
            continue
    content = card(760, 182, "RECENT ACTIVITY")
    for index in range(90):
        date = today - timedelta(days=89 - index)
        level = min(4, counts[date])
        x = 24 + (index % 45) * 15
        y = 49 + (index // 45) * 15
        delay = index * 0.025
        content += (
            f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" fill="{ACCENTS[level]}">'
            f'<animate attributeName="opacity" values=".45;1;.45" dur="3s" '
            f'begin="{delay:.3f}s" repeatCount="indefinite"/></rect>'
        )
    content += text("last 90 days · commits, issues and pull requests", 24, 145, 11, MUTED)
    write("activity.svg", svg(760, 182, content))


def make_streak(events):
    dates = {event.get("created_at", "")[:10] for event in events}
    streak = 0
    day = datetime.now(timezone.utc).date()
    while day.isoformat() in dates:
        streak += 1
        day -= timedelta(days=1)
    content = card(760, 112, "CURRENT STREAK")
    content += text(streak, 28, 78, 32, INK, "700")
    content += text("days", 84, 76, 14, MUTED)
    content += text("based on recent public GitHub activity", 24, 96, 11, MUTED)
    write("streak.svg", svg(760, 112, content))


def main():
    user = api(f"/users/{USERNAME}")
    repos = api(f"/users/{USERNAME}/repos?per_page=100&sort=updated")
    for repo in repos:
        if repo.get("fork") or not repo.get("languages_url"):
            continue
        repo["languages"] = api(repo["languages_url"].replace("https://api.github.com", ""))
    events = api(f"/users/{USERNAME}/events/public?per_page=100")
    language_totals = Counter()
    for repo in repos:
        language_totals.update(repo.get("languages") or {})
    make_stack(language_totals)
    make_stats(user, repos)
    make_languages(repos)
    make_activity(events)
    make_streak(events)


if __name__ == "__main__":
    main()
