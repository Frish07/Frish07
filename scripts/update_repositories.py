"""Build profile cards from GitHub's public repository API (standard library only)."""

import hashlib
import html
import json
import os
from pathlib import Path
import textwrap
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OWNER = "Frish07"
START = "<!-- POPULAR-REPOS:START -->"
END = "<!-- POPULAR-REPOS:END -->"
COLORS = {
    "Python": "#3572A5", "Java": "#b07219", "C++": "#f34b7d",
    "C#": "#178600", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "HTML": "#e34c26", "CSS": "#663399", "Rust": "#dea584",
    "Go": "#00ADD8", "Kotlin": "#A97BFF", "Shell": "#89e051",
}


def fetch_repositories():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Frish07-profile",
               "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}"
        with urlopen(Request(url, headers=headers), timeout=30) as response:
            batch = json.load(response)
        repos.extend(batch)
        if len(batch) < 100:
            return repos
        page += 1


def top_repositories(repos):
    eligible = [r for r in repos if not r.get("fork") and not r.get("private")
                and r["name"].lower() != OWNER.lower()
                and r["owner"]["login"].lower() == OWNER.lower()]
    return sorted(eligible, key=lambda r: (-r["stargazers_count"], r["name"].casefold()))[:6]


def clean(value):
    return " ".join(str(value).split())


def card_svg(repo, theme):
    dark = theme == "dark"
    bg, border, title, muted = (("#0d1117", "#30363d", "#58a6ff", "#9198a1") if dark
                                else ("#ffffff", "#d1d9e0", "#0969da", "#59636e"))
    name = clean(repo["name"])
    # Keep long names readable inside the badge boundary.
    title_lines = textwrap.wrap(name, width=43)[:2]
    if len(name) > 86:
        title_lines[-1] = title_lines[-1][:40] + "…"
    description = clean(repo.get("description") or "Описание пока не добавлено.")
    lines = textwrap.wrap(description, width=61)
    if len(lines) > 2:
        lines = lines[:2]
        lines[-1] = lines[-1][:58].rstrip() + "…"
    language = repo.get("language") or "Без языка"
    color = COLORS.get(language, "#8b949e")
    title_text = "".join(f'<tspan x="22" dy="{0 if i == 0 else 21}">{html.escape(line)}</tspan>'
                         for i, line in enumerate(title_lines))
    desc_text = "".join(f'<tspan x="22" dy="{0 if i == 0 else 22}">{html.escape(line)}</tspan>'
                        for i, line in enumerate(lines))
    label = html.escape(f'{name}: {repo["stargazers_count"]} stars, {language}', quote=True)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="550" height="192" viewBox="0 0 550 192" role="img" aria-label="{label}">
  <title>{label}</title>
  <rect x="0.5" y="0.5" width="549" height="191" rx="8" fill="{bg}" stroke="{border}"/>
  <g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">
    <text y="35" fill="{title}" font-size="17" font-weight="600">{title_text}</text>
    <rect x="471" y="20" width="58" height="23" rx="11.5" fill="none" stroke="{border}"/>
    <text x="500" y="36" text-anchor="middle" fill="{muted}" font-size="12">Public</text>
    <text y="94" fill="{muted}" font-size="14">{desc_text}</text>
    <circle cx="29" cy="161" r="7" fill="{color}"/>
    <text x="43" y="166" fill="{muted}" font-size="13">{html.escape(language)}</text>
    <g transform="translate(205 153)" fill="none" stroke="{muted}" stroke-width="1.5" stroke-linejoin="round">
      <path d="m8 0 2.5 5.1 5.6.8-4 4 .9 5.6-5-2.7-5 2.7.9-5.6-4-4 5.6-.8Z"/>
    </g>
    <text x="229" y="166" fill="{muted}" font-size="13">{repo["stargazers_count"]}</text>
  </g>
</svg>
'''


def update(root, repos):
    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("README must contain exactly one pair of repository markers")
    before, rest = readme.split(START)
    old, after = rest.split(END)
    cards = root / "assets" / "repositories"
    cards.mkdir(parents=True, exist_ok=True)
    entries = []
    generated = set()
    for index, repo in enumerate(top_repositories(repos), 1):
        sources = {}
        for theme in ("dark", "light"):
            svg = card_svg(repo, theme)
            # Content hashes change the image URL only when its data changes.
            digest = hashlib.sha256(svg.encode()).hexdigest()[:12]
            name = f"{index}-{theme}-{digest}.svg"
            (cards / name).write_text(svg, encoding="utf-8", newline="\n")
            generated.add(name)
            sources[theme] = f"assets/repositories/{name}"
        url = f'https://github.com/{OWNER}/{repo["name"]}'
        alt = html.escape(f'{repo["name"]} — {repo["stargazers_count"]} stars', quote=True)
        entries.append(f'''  <a href="{html.escape(url, quote=True)}">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="{sources['dark']}">
      <img src="{sources['light']}" alt="{alt}" width="49%">
    </picture>
  </a>''')
    body = "<p>\n" + "\n".join(entries) + "\n</p>" if entries else "Публичные проекты скоро появятся здесь."
    readme_path.write_text(before + START + "\n" + body + "\n" + END + after,
                           encoding="utf-8", newline="\n")
    for path in cards.glob("*.svg"):
        if path.name not in generated:
            path.unlink()
    print(f"Updated {len(entries)} repository cards.")


if __name__ == "__main__":
    update(ROOT, fetch_repositories())
