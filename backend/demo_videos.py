"""
demo_videos.py — Pre-load 3 demo songs into the Music AI Chatbot.

Run this ONCE after Railway deploys to populate the server with demo data
so you can show the app immediately during your presentation.

Usage:
    # Against your live Railway deployment:
    BACKEND_URL=https://your-app.railway.app python demo_videos.py

    # Against local server (for testing this script):
    BACKEND_URL=http://localhost:8000 python demo_videos.py

All 3 songs are major-label releases with guaranteed YouTube captions,
so the fast youtube-transcript-api path is used (no AssemblyAI needed).
"""

import os
import time
import httpx

# ── Demo videos ────────────────────────────────────────────────────────────────
# Chosen criteria:
#   1. Official music video (guaranteed captions)
#   2. Different genres (pop, hip-hop, latin) — shows the agent works broadly
#   3. High word count — more transcript = better RAG results in the demo

DEMO_VIDEOS = [
    {
        "title": "Taylor Swift — Anti-Hero",
        "url": "https://www.youtube.com/watch?v=b1kbLwvqugk",
        "note": "Pop — great for lyrics + marketing analysis",
    },
    {
        "title": "Bad Bunny — Me Porto Bonito",
        "url": "https://www.youtube.com/watch?v=OdEMBSOk07E",
        "note": "Latin trap — tests multilingual transcript handling",
    },
    {
        "title": "Drake — Rich Flex (feat. 21 Savage)",
        "url": "https://www.youtube.com/watch?v=lP-5oFJJWrE",
        "note": "Hip-hop — great for Spotify artist_info demo",
    },
]

# ── Config ────────────────────────────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
TIMEOUT_SECONDS = 120  # transcription can take a while


def check_health() -> bool:
    """Verify the backend is reachable before loading videos."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=10)
        data = response.json()
        print(f"[demo] Backend health: {data}")
        return data.get("status") == "ok"
    except Exception as e:
        print(f"[demo] ERROR: Cannot reach backend at {BACKEND_URL}: {e}")
        return False


def load_video(video: dict) -> bool:
    """
    Call POST /analyze for one video.
    Returns True on success, False on failure.
    """
    print(f"\n[demo] Loading: {video['title']}")
    print(f"[demo] URL: {video['url']}")
    print(f"[demo] Note: {video['note']}")

    try:
        response = httpx.post(
            f"{BACKEND_URL}/analyze",
            json={"youtube_url": video["url"]},
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code == 200:
            data = response.json()
            print(f"[demo] ✓ Success!")
            print(f"[demo]   video_id:      {data.get('video_id')}")
            print(f"[demo]   title:         {data.get('title')}")
            print(f"[demo]   channel:       {data.get('channel')}")
            print(f"[demo]   word_count:    {data.get('word_count')}")
            print(f"[demo]   chunks:        {data.get('chunks_created')}")
            print(f"[demo]   source:        {data.get('source')}")
            return True
        else:
            print(f"[demo] ✗ Failed — HTTP {response.status_code}: {response.text}")
            return False

    except httpx.TimeoutException:
        print(f"[demo] ✗ Timeout after {TIMEOUT_SECONDS}s — the AssemblyAI fallback may be running")
        print(f"[demo]   Try again with a video that has guaranteed captions")
        return False
    except Exception as e:
        print(f"[demo] ✗ Error: {e}")
        return False


def main():
    print("=" * 60)
    print("  Music AI Chatbot — Demo Video Loader")
    print("=" * 60)
    print(f"\n[demo] Target backend: {BACKEND_URL}")
    print(f"[demo] Loading {len(DEMO_VIDEOS)} demo videos...\n")

    # Step 1: Verify backend is up
    if not check_health():
        print("\n[demo] ABORT: Backend not reachable. Deploy to Railway first.")
        print(f"[demo] Then run: BACKEND_URL=https://your-app.railway.app python demo_videos.py")
        return

    # Step 2: Load each video
    results = []
    for i, video in enumerate(DEMO_VIDEOS, 1):
        print(f"\n── Video {i}/{len(DEMO_VIDEOS)} {'─' * 40}")
        success = load_video(video)
        results.append((video["title"], success))

        # Small pause between requests to avoid rate limits
        if i < len(DEMO_VIDEOS):
            print("[demo] Waiting 3 seconds before next video...")
            time.sleep(3)

    # Step 3: Summary
    print("\n" + "=" * 60)
    print("  Results")
    print("=" * 60)
    for title, success in results:
        status = "✓" if success else "✗"
        print(f"  {status}  {title}")

    total = len(results)
    passed = sum(1 for _, s in results if s)
    print(f"\n[demo] {passed}/{total} videos loaded successfully")

    if passed == total:
        print("[demo] All demo videos ready! You can now present from the live URL. 🎵")
    else:
        print("[demo] Some videos failed. Check the errors above and retry.")


if __name__ == "__main__":
    main()
