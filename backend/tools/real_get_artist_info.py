# backend/tools/get_artist_info.py
# Tool 4: get_artist_info
# Calls the Spotify Web API (client credentials flow) to fetch real artist data.
# No user OAuth needed — just your Spotify app client ID and secret.
# Steps: 1) get access token, 2) search artist by name, 3) fetch artist details.
# No LLM involved — pure HTTP calls to Spotify.

import httpx
from langchain_core.tools import tool
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"


def _get_spotify_token() -> str:
    """
    Fetches a Spotify access token using client credentials flow.
    Token is valid for 1 hour. Called internally before every API request.
    Not cached here — simple and stateless for school project scope.
    """
    print("   Fetching Spotify access token...")

    try:
        response = httpx.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        print("   ✅ Spotify token obtained")
        return token

    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Spotify auth failed (HTTP {e.response.status_code}). "
            "Check your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env"
        )
    except Exception as e:
        raise RuntimeError(f"Could not connect to Spotify: {str(e)}")


def _search_artist(token: str, artist_name: str) -> dict | None:
    """
    Searches Spotify for an artist by name and returns the best match.
    Returns the full artist object or None if not found.
    """
    print(f"   Searching Spotify for artist: '{artist_name}'")

    try:
        response = httpx.get(
            f"{SPOTIFY_API_BASE}/search",
            params={
                "q": artist_name,
                "type": "artist",
                "limit": 1
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        response.raise_for_status()
        items = response.json().get("artists", {}).get("items", [])

        if not items:
            print(f"   No artist found for '{artist_name}'")
            return None

        artist = items[0]
        print(f"   Found: {artist['name']} (id: {artist['id']})")
        return artist

    except Exception as e:
        print(f"   ❌ Spotify search error: {str(e)}")
        return None


def _get_top_tracks(token: str, artist_id: str) -> list[str]:
    """
    Fetches the top 5 track names for an artist from Spotify.
    Uses market=US as default — required by the Spotify top-tracks endpoint.
    """
    try:
        response = httpx.get(
            f"{SPOTIFY_API_BASE}/artists/{artist_id}/top-tracks",
            params={"market": "US"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0
        )
        response.raise_for_status()
        tracks = response.json().get("tracks", [])
        return [t["name"] for t in tracks[:5]]

    except Exception as e:
        print(f"   ❌ Error fetching top tracks: {str(e)}")
        return []


@tool
def get_artist_info(artist_name: str) -> str:
    """
    Fetch real-time artist data from Spotify including popularity score,
    genres, follower count, and top tracks.
    Use this tool when the user asks about the artist behind the song —
    their popularity, what genre they are, how many followers they have,
    or what their biggest songs are.

    Args:
        artist_name: The name of the artist to look up (e.g. 'Harry Styles').
    """
    print(f"\n🎤 [get_artist_info] Looking up artist: '{artist_name}'")

    try:
        # Step 1 — Authenticate with Spotify
        token = _get_spotify_token()

        # Step 2 — Search for the artist
        artist = _search_artist(token, artist_name)

        if not artist:
            return f"Could not find '{artist_name}' on Spotify. Try checking the spelling."

        # Step 3 — Fetch top tracks
        top_tracks = _get_top_tracks(token, artist["id"])

        # Step 4 — Format and return all data
        name = artist["name"]
        followers = artist.get("followers", {}).get("total", 0)
        popularity = artist.get("popularity", 0)  # 0-100 Spotify score
        genres = artist.get("genres", [])
        spotify_url = artist.get("external_urls", {}).get("spotify", "")

        # Format followers with comma separators for readability
        followers_formatted = f"{followers:,}"

        genres_str = ", ".join(genres) if genres else "Not categorized"
        tracks_str = "\n  - ".join(top_tracks) if top_tracks else "No data available"

        result = f"""SPOTIFY ARTIST DATA — {name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Followers:      {followers_formatted}
Popularity:     {popularity}/100 (Spotify score)
Genres:         {genres_str}

Top Tracks:
  - {tracks_str}

Spotify Profile: {spotify_url}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Note: Popularity score is Spotify's internal metric (0-100),
based on recent stream counts relative to all artists on the platform."""

        print(f"   ✅ Artist data retrieved for {name}")
        return result

    except RuntimeError as e:
        # Auth or connection errors from helper functions
        return f"Spotify error: {str(e)}"
    except Exception as e:
        error_msg = f"Unexpected error fetching artist info for '{artist_name}': {str(e)}"
        print(f"   ❌ {error_msg}")
        return error_msg