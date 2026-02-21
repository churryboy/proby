#!/usr/bin/env python3
"""
Social Listening - Multi-Platform Collector
Collects mentions from Reddit, Twitter/X, Threads, Instagram, Facebook, LinkedIn(limited), TikTok(limited).
Outputs to Obsidian vault as markdown.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import Path Abstraction Layer
try:
    from vault_path import get_vault_root, get_file_path
except ModuleNotFoundError:
    current_dir = Path(__file__).resolve().parent
    for candidate in [current_dir.parent, current_dir.parent.parent]:
        if candidate and (candidate / "vault_path").exists():
            sys.path.insert(0, str(candidate))
            break
    from vault_path import get_vault_root, get_file_path

VAULT_ROOT = get_vault_root()
MARKET_RESEARCH_FOLDER = get_file_path("market_research_folder", must_exist=True)
OUTPUT_SUBFOLDER = "시장조사 스크랩/Social Listening"
OUTPUT_SUBFOLDER_FALLBACK = "10. 전략팀/리서치 애널리스트/Social Listening"

# Default keywords to monitor (market research / Proby related)
DEFAULT_KEYWORDS = [
    "user research",
    "usability testing",
    "market research",
    "qualitative research",
    "Proby",
    "Listen Labs",
]

# Platform-specific subreddits / hashtags
REDDIT_SUBREDDITS = [
    "UserResearch",
    "UXResearch",
    "marketresearch",
    "SaaS",
    "startups",
]
INSTAGRAM_HASHTAGS = ["userresearch", "uxresearch", "marketresearch"]
FACEBOOK_PAGE_IDS: List[str] = []  # Add page IDs to monitor (e.g. "123456789")


def load_env() -> None:
    """Load .env from project root."""
    try:
        from dotenv import load_dotenv
        script_dir = Path(__file__).resolve().parent
        for p in [script_dir / ".env", script_dir.parent / ".env", VAULT_ROOT / ".env", Path.cwd() / ".env"]:
            if p and p.exists():
                load_dotenv(dotenv_path=str(p))
                break
    except Exception:
        pass


# --- Reddit ---
def collect_reddit(keywords: List[str], limit_per_sub: int = 25) -> List[Dict[str, Any]]:
    """Collect posts from Reddit using PRAW."""
    posts: List[Dict[str, Any]] = []
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("[Reddit] SKIP: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET not set")
        return posts

    try:
        import praw
    except ImportError:
        print("[Reddit] SKIP: pip install praw")
        return posts

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent="SocialListener/1.0 (Proby research)",
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    seen = set()

    for sub_name in REDDIT_SUBREDDITS:
        try:
            sub = reddit.subreddit(sub_name)
            for post in sub.new(limit=limit_per_sub):
                if post.id in seen:
                    continue
                created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                if created < cutoff:
                    continue
                text = f"{post.title} {post.selftext}".lower()
                if not any(kw.lower() in text for kw in keywords):
                    continue
                seen.add(post.id)
                posts.append({
                    "platform": "reddit",
                    "id": post.id,
                    "title": post.title,
                    "text": (post.selftext or "")[:500],
                    "url": f"https://reddit.com{post.permalink}",
                    "author": str(post.author),
                    "created_at": created.isoformat(),
                    "score": post.score,
                    "subreddit": sub_name,
                })
        except Exception as e:
            print(f"[Reddit] sub r/{sub_name}: {e}")

    # Also search by keyword
    try:
        for kw in keywords[:5]:  # Limit to avoid rate limits
            for post in reddit.subreddit("all").search(kw, time_filter="week", limit=20):
                if post.id in seen:
                    continue
                seen.add(post.id)
                created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
                posts.append({
                    "platform": "reddit",
                    "id": post.id,
                    "title": post.title,
                    "text": (post.selftext or "")[:500],
                    "url": f"https://reddit.com{post.permalink}",
                    "author": str(post.author),
                    "created_at": created.isoformat(),
                    "score": post.score,
                    "subreddit": post.subreddit.display_name,
                })
    except Exception as e:
        print(f"[Reddit] search: {e}")

    print(f"[Reddit] collected {len(posts)} posts")
    return posts


# --- Twitter / X ---
def collect_twitter(keywords: List[str], max_results: int = 50) -> List[Dict[str, Any]]:
    """Collect tweets using Twitter API v2."""
    tweets: List[Dict[str, Any]] = []
    bearer = os.environ.get("TWITTER_BEARER_TOKEN") or os.environ.get("X_BEARER_TOKEN")
    if not bearer:
        print("[Twitter] SKIP: TWITTER_BEARER_TOKEN or X_BEARER_TOKEN not set")
        return tweets

    try:
        import tweepy
    except ImportError:
        print("[Twitter] SKIP: pip install tweepy")
        return tweets

    query = " OR ".join(f'"{kw}"' for kw in keywords[:3])
    if len(query) > 500:
        query = " OR ".join(f'"{kw}"' for kw in keywords[:2])

    try:
        client = tweepy.Client(bearer_token=bearer)
        resp = client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 100),
            tweet_fields=["created_at", "public_metrics"],
            user_fields=["username"],
            expansions=["author_id"],
        )
        if not resp.data:
            print("[Twitter] no results")
            return tweets

        users = {u.id: u for u in (resp.includes.get("users") or [])}
        for t in resp.data:
            u = users.get(t.author_id)
            tweets.append({
                "platform": "twitter",
                "id": t.id,
                "title": "",
                "text": t.text[:500],
                "url": f"https://twitter.com/{u.username}/status/{t.id}" if u else f"https://x.com/i/status/{t.id}",
                "author": u.username if u else "unknown",
                "created_at": t.created_at.isoformat() if t.created_at else "",
                "metrics": t.public_metrics or {},
            })
        print(f"[Twitter] collected {len(tweets)} tweets")
    except Exception as e:
        print(f"[Twitter] error: {e}")

    return tweets


# --- Threads ---
def collect_threads(keywords: List[str], limit: int = 25) -> List[Dict[str, Any]]:
    """Collect Threads posts via Meta Graph API."""
    posts: List[Dict[str, Any]] = []
    token = os.environ.get("THREADS_ACCESS_TOKEN") or os.environ.get("META_ACCESS_TOKEN")
    if not token:
        print("[Threads] SKIP: THREADS_ACCESS_TOKEN not set")
        return posts

    import requests
    url = "https://graph.threads.net/v1.0/keyword_search"
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).timestamp()

    for kw in keywords[:5]:
        try:
            r = requests.get(
                url,
                params={
                    "q": kw,
                    "search_type": "RECENT",
                    "fields": "id,text,media_type,permalink,timestamp,username",
                    "access_token": token,
                    "limit": limit,
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            for item in data.get("data") or []:
                ts = item.get("timestamp", "")
                if ts:
                    try:
                        from dateutil import parser as dp
                        dt = dp.parse(ts)
                        if dt.timestamp() < cutoff:
                            continue
                    except Exception:
                        pass
                posts.append({
                    "platform": "threads",
                    "id": item.get("id", ""),
                    "title": "",
                    "text": (item.get("text") or "")[:500],
                    "url": item.get("permalink", f"https://threads.net/"),
                    "author": item.get("username", ""),
                    "created_at": ts,
                    "media_type": item.get("media_type", ""),
                })
        except Exception as e:
            print(f"[Threads] keyword '{kw}': {e}")

    # Dedupe by id
    seen = set()
    unique = []
    for p in posts:
        if p["id"] not in seen:
            seen.add(p["id"])
            unique.append(p)
    posts = unique
    print(f"[Threads] collected {len(posts)} posts")
    return posts


# --- Instagram ---
def collect_instagram(hashtags: List[str], limit: int = 20) -> List[Dict[str, Any]]:
    """Collect Instagram posts by hashtag via Graph API. Requires instagram_public_content_access."""
    posts: List[Dict[str, Any]] = []
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN") or os.environ.get("META_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")  # IG Business/Creator account ID
    if not token or not user_id:
        print("[Instagram] SKIP: INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID required")
        return posts

    import requests
    base = "https://graph.facebook.com/v21.0"

    for tag in hashtags[:10]:  # 30 hashtags per 7 days limit
        tag = tag.lstrip("#")
        try:
            # Get hashtag ID
            r = requests.get(
                f"{base}/ig_hashtag_search",
                params={"user_id": user_id, "q": tag, "access_token": token},
                timeout=10,
            )
            r.raise_for_status()
            ht_data = r.json()
            ht_id = ht_data.get("data", [{}])[0].get("id") if ht_data.get("data") else None
            if not ht_id:
                continue

            # Get recent media
            r2 = requests.get(
                f"{base}/{ht_id}/recent_media",
                params={
                    "user_id": user_id,
                    "fields": "id,caption,permalink,timestamp,username",
                    "access_token": token,
                    "limit": limit,
                },
                timeout=10,
            )
            r2.raise_for_status()
            media = r2.json()
            for m in media.get("data") or []:
                posts.append({
                    "platform": "instagram",
                    "id": m.get("id", ""),
                    "title": "",
                    "text": (m.get("caption") or "")[:500],
                    "url": m.get("permalink", ""),
                    "author": m.get("username", ""),
                    "created_at": m.get("timestamp", ""),
                })
        except Exception as e:
            print(f"[Instagram] #{tag}: {e}")

    print(f"[Instagram] collected {len(posts)} posts")
    return posts


# --- Facebook ---
def collect_facebook(page_ids: List[str], limit: int = 25) -> List[Dict[str, Any]]:
    """Collect posts from Facebook Pages you admin. For public post search, use Content Library API (requires approval)."""
    posts: List[Dict[str, Any]] = []
    token = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or os.environ.get("META_ACCESS_TOKEN")
    if not token:
        print("[Facebook] SKIP: FACEBOOK_PAGE_ACCESS_TOKEN not set")
        return posts
    if not page_ids:
        print("[Facebook] SKIP: Set FACEBOOK_PAGE_IDS env (comma-separated) to monitor pages")
        return posts

    import requests
    base = "https://graph.facebook.com/v21.0"
    page_list = os.environ.get("FACEBOOK_PAGE_IDS", "").split(",") or page_ids
    page_list = [p.strip() for p in page_list if p.strip()]

    for page_id in page_list[:5]:
        try:
            r = requests.get(
                f"{base}/{page_id}/posts",
                params={
                    "fields": "id,message,created_time,permalink_url",
                    "access_token": token,
                    "limit": limit,
                },
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            for p in data.get("data") or []:
                posts.append({
                    "platform": "facebook",
                    "id": p.get("id", ""),
                    "title": "",
                    "text": (p.get("message") or "")[:500],
                    "url": p.get("permalink_url", ""),
                    "author": page_id,
                    "created_at": p.get("created_time", ""),
                })
        except Exception as e:
            print(f"[Facebook] page {page_id}: {e}")

    print(f"[Facebook] collected {len(posts)} posts")
    return posts


# --- LinkedIn (limited) ---
def collect_linkedin(keywords: List[str]) -> List[Dict[str, Any]]:
    """LinkedIn does not offer public post search via official API.
    Options: 1) Use LinkedIn Marketing API with approved access 2) Third-party (LinkUp, etc.)
    This is a placeholder that documents the limitation."""
    print("[LinkedIn] SKIP: Official API does not support public post search. "
          "Consider: LinkedIn Marketing API (limited), or third-party data providers.")
    return []


# --- TikTok (limited) ---
def collect_tiktok(keywords: List[str]) -> List[Dict[str, Any]]:
    """TikTok Research API is for academic researchers only (approval required).
    Commercial access: TikTok for Developers - different product."""
    print("[TikTok] SKIP: Research API is academic-only. Commercial listening requires TikTok for Developers.")
    return []


# --- Output ---
def build_markdown(all_posts: List[Dict[str, Any]], keywords: List[str]) -> str:
    """Build aggregated markdown output."""
    today = datetime.now().strftime("%Y-%m-%d")
    by_platform: Dict[str, List] = {}
    for p in all_posts:
        pl = p.get("platform", "unknown")
        by_platform.setdefault(pl, []).append(p)

    lines = [
        "---",
        f"title: \"Social Listening Summary - {today}\"",
        f"date: {today}",
        f"total_posts: {len(all_posts)}",
        f"keywords: {keywords}",
        "---",
        "",
        f"# Social Listening Summary ({today})",
        "",
        f"**Keywords monitored**: {', '.join(keywords)}",
        "",
        f"**Total posts collected**: {len(all_posts)}",
        "",
        "## By Platform",
        "",
    ]
    for pl in ["reddit", "twitter", "threads", "instagram", "facebook"]:
        posts = by_platform.get(pl, [])
        lines.append(f"### {pl.capitalize()} ({len(posts)} posts)")
        lines.append("")
        for i, p in enumerate(posts[:30], 1):  # Max 30 per platform in summary
            title = p.get("title", "")
            text = (p.get("text") or "")[:200].replace("\n", " ")
            url = p.get("url", "")
            author = p.get("author", "")
            created = p.get("created_at", "")[:19] if p.get("created_at") else ""
            block = f"- **[{i}]** "
            if title:
                block += f"{title} "
            if text:
                block += f"— {text}..."
            block += f" — [🔗]({url}) @{author} ({created})"
            lines.append(block)
        if len(posts) > 30:
            lines.append(f"- ... and {len(posts) - 30} more")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    load_env()
    keywords = DEFAULT_KEYWORDS
    if len(sys.argv) > 1:
        keywords = [k.strip() for k in sys.argv[1].split(",") if k.strip()] or keywords

    all_posts: List[Dict[str, Any]] = []

    all_posts.extend(collect_reddit(keywords))
    all_posts.extend(collect_twitter(keywords))
    all_posts.extend(collect_threads(keywords))
    all_posts.extend(collect_instagram(INSTAGRAM_HASHTAGS))
    all_posts.extend(collect_facebook(FACEBOOK_PAGE_IDS))
    collect_linkedin(keywords)   # placeholder
    collect_tiktok(keywords)     # placeholder

    # Sort by date
    def sort_key(p):
        t = p.get("created_at") or ""
        return t

    all_posts.sort(key=sort_key, reverse=True)

    # Output
    if MARKET_RESEARCH_FOLDER and MARKET_RESEARCH_FOLDER.exists():
        out_dir = MARKET_RESEARCH_FOLDER / "Social Listening"
    else:
        out_dir = VAULT_ROOT / OUTPUT_SUBFOLDER_FALLBACK
    out_dir.mkdir(parents=True, exist_ok=True)

    md = build_markdown(all_posts, keywords)
    fname = f"{datetime.now().strftime('%Y-%m-%d')} - Social Listening.md"
    out_path = out_dir / fname
    out_path.write_text(md, encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
