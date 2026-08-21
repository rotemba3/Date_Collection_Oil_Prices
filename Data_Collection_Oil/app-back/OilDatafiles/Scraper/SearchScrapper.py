"""
Module for scraping tweets using twikit (cookie-based, no browser).

CHANGED FROM THE SELENIUM VERSION:
- Constructor now takes a twikit.Client instead of a Selenium webdriver.
- scrape_twitter_query() now takes a search QUERY STRING (e.g.
  '(from:username) since:2026-06-01 until:2026-06-10') instead of a full
  x.com search URL, since twikit talks to X's API directly rather than
  loading a page. main.py builds this query string instead of a URL now.
- Internally uses asyncio.run() so the rest of the codebase (main.py, etc.)
  doesn't have to become async — scrape_twitter_query() is still called
  as a normal, synchronous function.

Everything else (the Tweet class, the returned data shape, the method
name) is unchanged so the rest of the pipeline doesn't need to change.

Author: [Your Name]
Date: [Update Date]
"""

import asyncio


class Tweet:
    """
    Represents a tweet scraped from Twitter.

    Attributes:
    - ID: Unique identifier for the tweet.
    - author: Username of the tweet's author.
    - fullName: Full name of the tweet's author.
    - content: Text content of the tweet.
    - timestamp: Timestamp of the tweet.
    - retweets: Number of retweets.
    - likes: Number of likes.
    - hashtag: Hashtag associated with the tweet.
    - views: Number of views.
    - comments: Number of comments.
    - bookmarks: Number of bookmarks.
    - image_url: URL of the attached image.
    - video_url: URL of the attached video (if any).
    - video_preview_image_url: URL of the video preview image.
    - hashtags: List of hashtags used in the tweet.
    - url: URL of the tweet.
    """
    def __init__(self, ID, author, fullName, content, timestamp, retweets, likes, hashtag, views, comments, bookmarks, image_url, video_url=None, video_preview_image_url=None, hashtags=None, url=None):
        self.ID = ID
        self.author = author
        self.fullName = fullName
        self.content = content
        self.timestamp = timestamp
        self.retweets = retweets
        self.likes = likes
        self.hashtag = hashtag
        self.views = views
        self.comments = comments
        self.bookmarks = bookmarks
        self.image_url = image_url
        self.video_url = video_url
        self.video_preview_image_url = video_preview_image_url
        self.hashtags = hashtags
        self.url = url

    def __eq__(self, other):
        return isinstance(other, Tweet) and self.ID == other.ID

    def __hash__(self):
        return hash(self.ID)


class SearchScrapper:
    """
    Scraper for Twitter (X) search queries, using twikit.

    Methods:
    - scrape_twitter_query(query, hashtag, max_tweets): Scrapes tweets based
      on a twikit search query string (NOT a URL — see module docstring).
    """
    def __init__(self, client):
        """
        Initializes the SearchScrapper with a twikit.Client instance
        that has already been authenticated (cookies loaded).

        Parameters:
        - client (twikit.Client): An authenticated twikit client.
        """
        self.client = client

    def scrape_twitter_query(self, query: str, hashtag: str, max_tweets: int):
        """
        Scrapes tweets from a given twikit search query.

        Parameters:
        - query (str): twikit search query string, e.g.
          '(from:someuser) since:2026-06-01 until:2026-06-10'.
        - hashtag (str): Associated label for the search (kept from the
          original signature — used here as the "publisher"/username tag).
        - max_tweets (int): Maximum number of tweets to scrape.

        Returns:
        - set[Tweet]: A set of Tweet objects containing scraped data.
        """
        return asyncio.run(self._scrape_async(query, hashtag, max_tweets))

    async def _scrape_async(self, query: str, hashtag: str, max_tweets: int):
        import re

        tweets_out = set()
        processed_ids = set()

        try:
            result = await self.client.search_tweet(query, product="Latest")
        except Exception as e:
            print(f"Search failed for query '{query}': {e}")
            return tweets_out

        if not result:
            print(f"No results found for: {hashtag}")
            return tweets_out

        while result and len(tweets_out) < max_tweets:
            for t in result:
                if len(tweets_out) >= max_tweets:
                    break

                tweet_id = str(getattr(t, "id", None))
                if not tweet_id or tweet_id in processed_ids:
                    continue
                processed_ids.add(tweet_id)

                content = getattr(t, "full_text", None) or getattr(t, "text", None)
                author = getattr(getattr(t, "user", None), "screen_name", hashtag)
                full_name = getattr(getattr(t, "user", None), "name", None)
                timestamp = getattr(t, "created_at", "No timestamp available")
                retweet_count = getattr(t, "retweet_count", 0)
                like_count = getattr(t, "favorite_count", 0)
                comments = getattr(t, "reply_count", 0)
                bookmarks = getattr(t, "bookmark_count", 0)
                views = getattr(t, "view_count", None)
                url = f"https://x.com/{author}/status/{tweet_id}"
                hashtags = re.findall(r'#\w+', content or "")

                image_url = None
                video_url = None
                video_preview_image_url = None
                media = getattr(t, "media", None)
                if media:
                    for m in media:
                        m_type = getattr(m, "type", None)
                        if m_type == "photo" and image_url is None:
                            image_url = getattr(m, "media_url_https", None)
                        elif m_type in ("video", "animated_gif") and video_url is None:
                            video_preview_image_url = getattr(m, "media_url_https", None)

                tweets_out.add(Tweet(
                    ID=tweet_id, author=author, fullName=full_name, content=content,
                    timestamp=timestamp, retweets=retweet_count, likes=like_count,
                    hashtag=hashtag, views=views, comments=comments, bookmarks=bookmarks,
                    image_url=image_url, video_url=video_url,
                    video_preview_image_url=video_preview_image_url,
                    hashtags=hashtags, url=url
                ))

            if len(tweets_out) >= max_tweets:
                break

            try:
                result = await result.next()
            except Exception as e:
                print(f"Pagination stopped for '{query}': {e}")
                break

        print(f"Scraping complete for {hashtag}: {len(tweets_out)} tweets.")
        return tweets_out
