# backend/evaluation.py
# -------------------------------------------------------
# Day 5 — Evaluation
# Runs 5 question/answer test pairs against the live agent.
# Results are printed to terminal — screenshot for your slides.
#
# How to run:
#   cd backend
#   python evaluation.py
#
# You will be prompted to enter the video ID, title, and artist.
# Make sure you have already run POST /analyze on the video first
# so the transcript exists in ChromaDB.
#
# What it tests:
#   1. Song theme/meaning       → search_transcript
#   2. Lyrics request           → extract_lyrics
#   3. Marketing analysis       → search_transcript + analyze_marketing_potential
#   4. Release timing           → find_release_timing
#   5. Spotify pitch how-to     → search_marketing_knowledge
# -------------------------------------------------------

import asyncio
import json
import uuid
from datetime import datetime

from agent import create_music_agent, run_agent

# -------------------------------------------------------
# 5 evaluation test pairs
# Questions are generic — work for any song
# -------------------------------------------------------
TEST_PAIRS = [
    {
        "id": "eval_01",
        "description": "Song theme and meaning",
        "question": "What is this song about? What are the main themes?",
        "expected_keywords": ["song", "theme", "lyrics", "meaning"],
        "expected_tools": ["search_transcript"],
    },
    {
        "id": "eval_02",
        "description": "Lyrics extraction",
        "question": "Can you show me the full lyrics of this song?",
        "expected_keywords": ["lyrics", "verse", "chorus"],
        "expected_tools": ["extract_lyrics"],
    },
    {
        "id": "eval_03",
        "description": "Marketing analysis with genre detection",
        "question": "Analyze the marketing potential of this song. What genre is it and who is the target audience?",
        "expected_keywords": ["genre", "audience", "tiktok", "platform"],
        "expected_tools": ["search_transcript", "analyze_marketing_potential"],
    },
    {
        "id": "eval_04",
        "description": "Release timing strategy",
        "question": "When is the best time to release this song and what should the release strategy look like?",
        "expected_keywords": ["release", "week", "strategy", "platform"],
        "expected_tools": ["find_release_timing"],
    },
    {
        "id": "eval_05",
        "description": "Marketing knowledge — Spotify pitch",
        "question": "How do I pitch this song to Spotify editorial playlists?",
        "expected_keywords": ["spotify", "pitch", "playlist", "submit"],
        "expected_tools": ["search_marketing_knowledge"],
    },
]


# -------------------------------------------------------
# Evaluator
# -------------------------------------------------------
def evaluate_response(test: dict, response: str, tools_used: list) -> dict:
    response_lower = response.lower()

    keywords_found = [
        kw for kw in test["expected_keywords"]
        if kw.lower() in response_lower
    ]
    keyword_score = len(keywords_found) / len(test["expected_keywords"])

    tools_found = [
        t for t in test["expected_tools"]
        if t in tools_used
    ]
    tool_score = len(tools_found) / len(test["expected_tools"])

    passed = keyword_score >= 0.5 and tool_score >= 0.5

    return {
        "test_id": test["id"],
        "description": test["description"],
        "passed": passed,
        "keyword_score": round(keyword_score, 2),
        "tool_score": round(tool_score, 2),
        "overall_score": round((keyword_score + tool_score) / 2, 2),
        "keywords_found": keywords_found,
        "keywords_missing": [
            kw for kw in test["expected_keywords"]
            if kw.lower() not in response_lower
        ],
        "tools_used": tools_used,
        "tools_expected": test["expected_tools"],
        "tools_missing": [
            t for t in test["expected_tools"]
            if t not in tools_used
        ],
        "response_length": len(response),
        "response_preview": response[:200] + "..." if len(response) > 200 else response,
    }


# -------------------------------------------------------
# Main
# -------------------------------------------------------
async def run_evaluation():
    print("\n" + "="*60)
    print("🎵 MUSIC AI CHATBOT — EVALUATION RUN")
    print("="*60)

    # Ask for video details at runtime — works for any song
    print("\nEnter the video details to evaluate against.")
    print("(The video must already be analyzed via POST /analyze)\n")

    video_id      = input("YouTube Video ID (e.g. H5v3kku4y6Q): ").strip()
    video_title   = input("Song title:                           ").strip()
    video_channel = input("Artist name:                          ").strip()

    if not video_id:
        print("\n❌ Video ID is required. Exiting.")
        return

    print(f"\n{'─'*60}")
    print(f"Video ID:  {video_id}")
    print(f"Title:     {video_title or '(not provided)'}")
    print(f"Artist:    {video_channel or '(not provided)'}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests:     {len(TEST_PAIRS)}")
    print("─"*60)

    print("\n🤖 Creating agent...")
    agent = create_music_agent()
    print("✅ Agent ready\n")

    results = []

    for i, test in enumerate(TEST_PAIRS, 1):
        print(f"\n{'─'*60}")
        print(f"TEST {i}/5 — {test['description']}")
        print(f"Question: {test['question']}")
        print("─"*60)

        # Each test gets its own session so memory doesn't bleed between tests
        session_id = f"eval_{test['id']}_{uuid.uuid4().hex[:8]}"

        try:
            result = await run_agent(
                agent=agent,
                message=test["question"],
                session_id=session_id,
                video_id=video_id,
                video_title=video_title,
                video_channel=video_channel,
            )

            response   = result.get("response", "")
            tools_used = result.get("tools_used", [])

            evaluation = evaluate_response(test, response, tools_used)
            results.append(evaluation)

            status = "✅ PASS" if evaluation["passed"] else "❌ FAIL"
            print(f"Status:         {status}")
            print(f"Tools used:     {tools_used if tools_used else 'none'}")
            print(f"Tools expected: {test['expected_tools']}")
            print(f"Keyword score:  {evaluation['keyword_score']} {evaluation['keywords_found']}")
            print(f"Tool score:     {evaluation['tool_score']}")
            print(f"Overall score:  {evaluation['overall_score']}")
            print(f"Response:       {evaluation['response_preview']}")

            if evaluation["keywords_missing"]:
                print(f"⚠️  Missing keywords: {evaluation['keywords_missing']}")
            if evaluation["tools_missing"]:
                print(f"⚠️  Missing tools:    {evaluation['tools_missing']}")

        except Exception as e:
            print(f"❌ Test crashed: {str(e)}")
            results.append({
                "test_id": test["id"],
                "description": test["description"],
                "passed": False,
                "overall_score": 0,
                "error": str(e),
            })

    # -------------------------------------------------------
    # Final summary — screenshot this for your slides
    # -------------------------------------------------------
    print("\n" + "="*60)
    print("📊 EVALUATION SUMMARY — screenshot this for your slides")
    print("="*60)

    passed    = sum(1 for r in results if r.get("passed", False))
    total     = len(results)
    avg_score = sum(r.get("overall_score", 0) for r in results) / total

    for r in results:
        status = "✅" if r.get("passed", False) else "❌"
        score  = r.get("overall_score", 0)
        print(f"  {status}  {r['test_id']} — {r['description']:<40} score: {score}")

    print("─"*60)
    print(f"  Song:      {video_title} — {video_channel}")
    print(f"  Passed:    {passed}/{total}")
    print(f"  Avg score: {round(avg_score, 2)}")
    print(f"  Grade:     {'EXCELLENT' if avg_score >= 0.8 else 'GOOD' if avg_score >= 0.6 else 'NEEDS WORK'}")
    print("="*60)

    # Save JSON for records
    output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "video_id": video_id,
            "video_title": video_title,
            "video_channel": video_channel,
            "timestamp": datetime.now().isoformat(),
            "passed": passed,
            "total": total,
            "avg_score": round(avg_score, 2),
            "results": results,
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Results saved to: {output_file}\n")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
