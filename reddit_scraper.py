"""Collect original Reddit home-repair posts for a risk-labeling dataset.

This scraper uses Reddit's public JSON listings and stores only the original
post title/body, not comments. The output is intentionally unlabeled; optional
review hints are included only to make manual labeling faster.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_SUBREDDITS = [
    "HomeImprovement",
    "HomeMaintenance",
    "DIY",
    "Plumbing",
    "askanelectrician",
    "hvacadvice",
    "Homeowners",
]

DEFAULT_QUERIES = [
    "leak",
    "gas smell",
    "loose trim",
    "mold",
    "sparking outlet",
    "paint peeling",
    "water leak",
    "caulk",
    "flooding",
    "electrical issue",
    "drywall patch",
    "foundation crack",
    "black mold",
    "water heater",
    "stain",
    "crack wall",
    "structural crack",
    "burning smell",
    "cosmetic fix",
    "breaker keeps tripping",
    "wiring",
    "hvac not working",
    "paint",
    "furnace",
    "roof leak",
    "loose knob",
    "sewer smell",
]

URGENT_PATTERNS = [
    r"\bgas smell\b",
    r"\bsmell of gas\b",
    r"\bnatural gas\b",
    r"\bspark(?:ing|s)?\b",
    r"\bsmoke\b",
    r"\bburning smell\b",
    r"\belectrical fire\b",
    r"\bflood(?:ing|ed)?\b",
    r"\bsewage backup\b",
    r"\bcarbon monoxide\b",
    r"\bco detector\b",
    r"\bstructural\b",
    r"\bceiling collapse\b",
    r"\bload[- ]bearing\b",
]

MEDIUM_PATTERNS = [
    r"\bleak(?:s|ing)?\b",
    r"\bmold\b",
    r"\bwater heater\b",
    r"\bfurnace\b",
    r"\bhvac\b",
    r"\bair conditioner\b",
    r"\bbreaker\b",
    r"\boutlets?\b",
    r"\bwiring\b",
    r"\bplumbing\b",
    r"\broof\b",
    r"\bfoundation\b",
    r"\bwater damage(?:d)?\b",
    r"\bwater intrusion\b",
    r"\bwater coming through\b",
]

LOW_PATTERNS = [
    r"\bpaint\b",
    r"\btrim\b",
    r"\bcaulk(?:ing)?\b",
    r"\bdrywall patch\b",
    r"\bcosmetic\b",
    r"\bscratch\b",
    r"\bstain\b",
    r"\bloose knob\b",
]


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file if it exists."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class RedditPost:
    reddit_id: str
    subreddit: str
    created_utc: str
    title: str
    selftext: str
    text: str
    permalink: str
    score: int
    num_comments: int
    url: str
    source_query: str
    review_hint: str
    label: str = ""


def clean_text(value: str) -> str:
    value = value.replace("\u200b", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def word_count(value: str) -> int:
    return len(re.findall(r"\b\w+\b", value))


def review_hint(text: str) -> str:
    lowered = text.lower()
    for pattern in URGENT_PATTERNS:
        if re.search(pattern, lowered):
            return "needs_review_urgent_signal"
    for pattern in MEDIUM_PATTERNS:
        if re.search(pattern, lowered):
            return "needs_review_medium_signal"
    for pattern in LOW_PATTERNS:
        if re.search(pattern, lowered):
            return "needs_review_low_signal"
    return "needs_review_unclear"


def request_json(url: str, user_agent: str, retries: int = 3) -> dict:
    headers = {"User-Agent": user_agent}
    request = Request(url, headers=headers)

    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                wait_seconds = 30 * attempt
                print(f"Rate limited. Waiting {wait_seconds}s before retrying.")
                time.sleep(wait_seconds)
                continue
            raise
        except URLError:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)

    return {}


def get_reddit_oauth_token(
    client_id: str,
    client_secret: str,
    user_agent: str,
    username: str | None = None,
    password: str | None = None,
) -> str:
    token_url = "https://www.reddit.com/api/v1/access_token"
    if username and password:
        body = urlencode(
            {
                "grant_type": "password",
                "username": username,
                "password": password,
            }
        ).encode("utf-8")
    else:
        body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")

    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    auth_header = base64.b64encode(credentials).decode("ascii")
    request = Request(
        token_url,
        data=body,
        headers={
            "Authorization": f"Basic {auth_header}",
            "User-Agent": user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Reddit OAuth token response did not include access_token")
    return token


def request_reddit_json(
    url: str, user_agent: str, oauth_token: str | None, retries: int = 3
) -> dict:
    if not oauth_token:
        return request_json(url, user_agent=user_agent, retries=retries)

    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "User-Agent": user_agent,
    }
    request = Request(url, headers=headers)
    for attempt in range(1, retries + 1):
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429 and attempt < retries:
                wait_seconds = 30 * attempt
                print(f"Rate limited. Waiting {wait_seconds}s before retrying.")
                time.sleep(wait_seconds)
                continue
            raise
        except URLError:
            if attempt == retries:
                raise
            time.sleep(5 * attempt)

    return {}


def build_search_url(
    subreddit: str,
    query: str,
    limit: int,
    after: str | None,
    use_oauth: bool,
) -> str:
    params = {
        "q": query,
        "restrict_sr": "1",
        "sort": "new",
        "t": "all",
        "limit": str(limit),
        "raw_json": "1",
    }
    if after:
        params["after"] = after
    host = "oauth.reddit.com" if use_oauth else "www.reddit.com"
    return f"https://{host}/r/{subreddit}/search.json?{urlencode(params)}"


def parse_post(data: dict, source_query: str, min_words: int) -> RedditPost | None:
    title = clean_text(data.get("title") or "")
    selftext = clean_text(data.get("selftext") or "")
    if not title or selftext.lower() in {"[removed]", "[deleted]"}:
        return None

    text = clean_text(f"{title}\n\n{selftext}") if selftext else title
    if word_count(text) < min_words:
        return None

    created = datetime.fromtimestamp(
        float(data.get("created_utc") or 0), tz=timezone.utc
    ).isoformat()

    permalink = data.get("permalink") or ""
    if permalink and permalink.startswith("/"):
        permalink = f"https://www.reddit.com{permalink}"

    return RedditPost(
        reddit_id=data.get("id") or "",
        subreddit=data.get("subreddit") or "",
        created_utc=created,
        title=title,
        selftext=selftext,
        text=text,
        permalink=permalink,
        score=int(data.get("score") or 0),
        num_comments=int(data.get("num_comments") or 0),
        url=data.get("url") or "",
        source_query=source_query,
        review_hint=review_hint(text),
    )


def scrape(
    subreddits: Iterable[str],
    queries: Iterable[str],
    max_posts: int,
    max_posts_per_subreddit: int | None,
    max_posts_per_query: int | None,
    per_request: int,
    pages_per_query: int,
    min_words: int,
    delay: float,
    user_agent: str,
    oauth_token: str | None,
) -> list[RedditPost]:
    posts: dict[str, RedditPost] = {}
    subreddit_counts: dict[str, int] = {}
    query_counts: dict[str, int] = {}
    use_oauth = oauth_token is not None

    for query in queries:
        for subreddit in subreddits:
            after = None
            for page in range(pages_per_query):
                if len(posts) >= max_posts:
                    return list(posts.values())
                if (
                    max_posts_per_query is not None
                    and query_counts.get(query.lower(), 0) >= max_posts_per_query
                ):
                    break
                if (
                    max_posts_per_subreddit is not None
                    and subreddit_counts.get(subreddit.lower(), 0) >= max_posts_per_subreddit
                ):
                    break

                url = build_search_url(
                    subreddit, query, per_request, after, use_oauth=use_oauth
                )
                print(
                    f"Fetching r/{subreddit} query={query!r} page={page + 1} "
                    f"collected={len(posts)}"
                )
                try:
                    payload = request_reddit_json(
                        url, user_agent=user_agent, oauth_token=oauth_token
                    )
                except HTTPError as exc:
                    if exc.code == 403 and not oauth_token:
                        raise RuntimeError(
                            "Reddit blocked the unauthenticated request. Create a "
                            "Reddit app and set REDDIT_CLIENT_ID and "
                            "REDDIT_CLIENT_SECRET, then run this command again."
                        ) from exc
                    raise
                listing = payload.get("data") or {}
                children = listing.get("children") or []
                after = listing.get("after")

                for child in children:
                    post_data = child.get("data") or {}
                    post = parse_post(post_data, query, min_words=min_words)
                    if post and post.reddit_id:
                        before_count = len(posts)
                        posts.setdefault(post.reddit_id, post)
                        if len(posts) > before_count:
                            key = post.subreddit.lower()
                            subreddit_counts[key] = subreddit_counts.get(key, 0) + 1
                            query_key = query.lower()
                            query_counts[query_key] = query_counts.get(query_key, 0) + 1
                        if len(posts) >= max_posts:
                            return list(posts.values())
                        if (
                            max_posts_per_query is not None
                            and query_counts.get(query.lower(), 0) >= max_posts_per_query
                        ):
                            break
                        if (
                            max_posts_per_subreddit is not None
                            and subreddit_counts.get(subreddit.lower(), 0)
                            >= max_posts_per_subreddit
                        ):
                            break

                time.sleep(delay)
                if not after:
                    break

    return list(posts.values())


def write_jsonl(posts: list[RedditPost], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for post in posts:
            handle.write(json.dumps(asdict(post), ensure_ascii=False) + "\n")


def write_csv(posts: list[RedditPost], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(posts[0]).keys()) if posts else list(RedditPost.__dataclass_fields__)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for post in posts:
            writer.writerow(asdict(post))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape original Reddit home-repair posts for manual labeling."
    )
    parser.add_argument("--max-posts", type=int, default=750)
    parser.add_argument(
        "--max-posts-per-subreddit",
        type=int,
        default=150,
        help="Cap each subreddit so the dataset covers multiple communities. Use 0 for no cap.",
    )
    parser.add_argument(
        "--max-posts-per-query",
        type=int,
        default=75,
        help="Cap each search query so the dataset covers multiple problem types. Use 0 for no cap.",
    )
    parser.add_argument("--per-request", type=int, default=100)
    parser.add_argument("--pages-per-query", type=int, default=2)
    parser.add_argument("--min-words", type=int, default=20)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--out-dir", type=Path, default=Path("data/raw"))
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Path to a .env file containing REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET.",
    )
    parser.add_argument("--subreddits", nargs="*", default=DEFAULT_SUBREDDITS)
    parser.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    parser.add_argument(
        "--user-agent",
        default=None,
        help="Identify this scraper to Reddit. Defaults to REDDIT_USER_AGENT from .env.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    load_env_file(args.env_file)
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")
    user_agent = (
        args.user_agent
        or os.getenv("REDDIT_USER_AGENT")
        or "home-repair-risk-ml-dataset/0.1 by student-project"
    )
    oauth_token = None
    if client_id and client_secret:
        print("Using Reddit OAuth credentials from environment variables.")
        oauth_token = get_reddit_oauth_token(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
            username=username,
            password=password,
        )
    else:
        print("No Reddit OAuth credentials found; trying public Reddit JSON.")

    posts = scrape(
        subreddits=args.subreddits,
        queries=args.queries,
        max_posts=args.max_posts,
        max_posts_per_subreddit=(
            None if args.max_posts_per_subreddit == 0 else args.max_posts_per_subreddit
        ),
        max_posts_per_query=(
            None if args.max_posts_per_query == 0 else args.max_posts_per_query
        ),
        per_request=args.per_request,
        pages_per_query=args.pages_per_query,
        min_words=args.min_words,
        delay=args.delay,
        user_agent=user_agent,
        oauth_token=oauth_token,
    )

    jsonl_path = args.out_dir / f"reddit_home_repair_posts_{timestamp}.jsonl"
    csv_path = args.out_dir / f"reddit_home_repair_posts_{timestamp}.csv"
    write_jsonl(posts, jsonl_path)
    write_csv(posts, csv_path)

    print(f"Saved {len(posts)} unique posts")
    print(f"JSONL: {jsonl_path}")
    print(f"CSV:   {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
