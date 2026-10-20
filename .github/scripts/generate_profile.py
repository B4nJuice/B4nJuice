#!/usr/bin/env python3
"""Generate monochrome SVG profile assets from GitHub's public API."""

import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from html import escape
from urllib.request import Request, urlopen

USERNAME = "B4nJuice"
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets")
INK = "#ffffff"
MUTED = "#ffffff"
GRID = "#ffffff"
ACCENTS = ("#d0d0d0", "#b8b8b8", "#9f9f9f", "#858585", "#ffffff")


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
        request.add_header("Authorization", "B" + "earer " + token)
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except Exception as error:
        print(f"GitHub API request failed for {path}: {error}", file=sys.stderr)
        raise


def svg(width, height, content):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}"><style>text{{font-family:"JetBrains Mono",'
        f'monospace}}</style>{content}</svg>\n'
    )


def contribution_calendar():
    query = """query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { contributionCount date } }
          }
        }
      }
    }"""
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode(),
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "B4nJuice-profile-generator",
            "Authorization": "B" + "earer " + os.environ["GITHUB_TOKEN"],
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL request failed: {payload['errors']}")
    return [
        day
        for week in payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for day in week["contributionDays"]
    ]


def text(value, x, y, size=14, fill=INK, weight="400", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'
    )


def card(width, height, title):
    return (
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="8" '
        f'fill="none" stroke="{GRID}" stroke-opacity=".25"/>{text(title, 24, 31, 13, MUTED, "600")}'
    )


def write(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as asset:
        asset.write(content)


def make_profile(user):
    avatar_url = escape(user["avatar_url"], quote=True)
    content = (
        '<defs><clipPath id="avatar-clip"><circle cx="88" cy="88" r="64"/></clipPath></defs>'
        f'<image href="{avatar_url}" x="24" y="24" '
        'width="128" height="128" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatar-clip)"/>'
        f'{text(user["login"], 184, 49, 24, INK, "700")}'
        f'{text("STACKS", 184, 78, 11, MUTED, "600")}'
        f'{text("Python · C · AI · Makefile", 184, 97, 12, INK)}'
        f'{text("ABOUT", 184, 124, 11, MUTED, "600")}'
        f'{text("42 Lyon student", 184, 143, 11, INK)}'
    )
    write("profile.svg", svg(760, 184, content))


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


def make_activity(days):
    values = [day["contributionCount"] for day in days]
    weekly = [sum(values[index:index + 7]) for index in range(0, len(values), 7)]
    total_contributions = sum(values)
    active_days = sum(value > 0 for value in values)
    best_week = max(weekly, default=0)
    content = card(760, 182, f"{total_contributions} CONTRIBUTIONS IN THE LAST YEAR")
    content += text(
        f"{active_days} ACTIVE DAYS · BEST WEEK {best_week}",
        736, 31, 10, MUTED, "600", "end"
    )
    maximum = max(weekly, default=0) or 1
    points = []
    last_index = max(0, len(weekly) - 1)
    for index, value in enumerate(weekly):
        x = 24 + index * (712 / last_index) if last_index else 24
        y = 135 - (value / maximum) * 78
        points.append(f"{x:.1f},{y:.1f}")
    point_string = " ".join(points)
    for fraction in (1, 0.5, 0):
        y = 135 - fraction * 78
        value = maximum * fraction
        label = f"{value:g}"
        content += (
            f'<line x1="24" y1="{y:g}" x2="736" y2="{y:g}" '
            f'stroke="{GRID}" stroke-opacity=".12"/>'
            f'{text(label, 4, y + 4, 9, MUTED, "400", "start")}'
        )
    content += (
        f'<polyline points="{point_string}" fill="none" stroke="{INK}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" pathLength="1" '
        f'stroke-dasharray="1" stroke-dashoffset="1">'
        f'<animate attributeName="stroke-dashoffset" from="1" to="0" '
        f'dur="2.8s" fill="freeze"/></polyline>'
    )
    for index, point in enumerate(points):
        x, y = point.split(",")
        content += (
            f'<circle cx="{x}" cy="{y}" r="2.5" fill="{INK}">'
            f'<animate attributeName="r" values="2.5;4;2.5" dur="2.4s" '
            f'begin="{index * 0.02:.2f}s" repeatCount="indefinite"/></circle>'
        )
    content += text("last year · all GitHub contributions", 24, 162, 11, MUTED)
    write("activity.svg", svg(760, 182, content))


def make_streak(events):
    dates = {event.get("created_at", "")[:10] for event in events}
    streak = 0
    day = datetime.now(UTC).date()
    while day.isoformat() in dates:
        streak += 1
        day -= timedelta(days=1)
    best_streak = 0
    best_end = None
    run = 0
    for day in sorted(datetime.strptime(date, "%Y-%m-%d").date() for date in dates):
        previous = day - timedelta(days=1)
        if previous.isoformat() in dates:
            run += 1
        else:
            run = 1
        if run > best_streak:
            best_streak = run
            best_end = day
    content = card(760, 112, "CURRENT STREAK")
    content += text(streak, 28, 78, 32, INK, "700")
    content += text("days", 84, 76, 14, MUTED)
    content += text("based on recent public GitHub activity", 24, 96, 11, MUTED)
    content += text("BEST STREAK", 520, 31, 13, MUTED, "600")
    content += text(best_streak, 524, 78, 32, INK, "700")
    content += text("days", 580, 76, 14, MUTED)
    best_date = best_end.strftime("%d %b %Y") if best_end else "No contribution streak"
    content += text(f"ending {best_date}", 520, 96, 11, MUTED)
    write("streak.svg", svg(760, 112, content))


def main():
    user = api(f"/users/{USERNAME}")
    repos = api(f"/users/{USERNAME}/repos?per_page=100&sort=updated")
    for repo in repos:
        if repo.get("fork") or not repo.get("languages_url"):
            continue
        repo["languages"] = api(repo["languages_url"].replace("https://api.github.com", ""))
    days = contribution_calendar()
    make_profile(user)
    make_languages(repos)
    make_activity(days)
    make_streak([{"created_at": day["date"]} for day in days if day["contributionCount"]])


if __name__ == "__main__":
    main()
