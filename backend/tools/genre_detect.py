# backend/tools/genre_detect.py
# -------------------------------------------------------
# Genre detection using Essentia Discogs-EffNet model.
#
# detect_genres(audio_path) → dict with:
#   top_genres   — list of {genre, subgenre, confidence}
#   all_genres   — full raw predictions sorted by confidence
#   source       — "essentia"
#
# Returns {} silently on any failure — never crashes the pipeline.
# -------------------------------------------------------

import os
import json
from unittest import loader

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

def detect_genres(audio_path: str) -> dict:
    print(f"[genre_detect] 🎵 Running Essentia genre detection on: {audio_path}")
    try:
        import numpy as np
        import essentia.standard as es

        # ── Load audio ──
        loader = es.MonoLoader(filename=audio_path, sampleRate=16000, resampleQuality=4)
        audio = loader()
        # Limit to first 60 seconds to avoid OOM on Render free tier
        audio = audio[:60 * 16000]
        model_path = os.path.join(MODELS_DIR, "discogs-effnet-bs64-1.pb")
        print(f"[genre_detect] Looking for model at: {os.path.abspath(model_path)}")
        print(f"[genre_detect] File exists: {os.path.exists(model_path)}")

        print(f"[genre_detect] Audio loaded: {len(audio) / 16000:.1f}s at 16000Hz")

        # ── Discogs-EffNet — audio → embeddings directly ──
        embedding_model = es.TensorflowPredictEffnetDiscogs(
            graphFilename=os.path.join(MODELS_DIR, "discogs-effnet-bs64-1.pb"),
            output="PartitionedCall:1",
        )
        embeddings = embedding_model(audio)
        print(f"[genre_detect] Embeddings shape: {embeddings.shape}")

        # ── Genre classifier ──
        genre_model = es.TensorflowPredict2D(
            graphFilename=os.path.join(MODELS_DIR, "genre_discogs400-discogs-effnet-1.pb"),
            input="serving_default_model_Placeholder",
            output="PartitionedCall:0",
        )
        raw_predictions = genre_model(embeddings)

        avg_predictions = np.mean(raw_predictions, axis=0)
        print(f"[genre_detect] Predictions averaged over {raw_predictions.shape[0]} patches")

        # ── Load label map ──
        labels_path = os.path.join(MODELS_DIR, "genre_discogs400-discogs-effnet-1.json")
        with open(labels_path, "r") as f:
            label_data = json.load(f)
        labels = label_data.get("classes", [])

        if len(labels) != len(avg_predictions):
            raise ValueError(
                f"Label count mismatch: {len(labels)} labels vs "
                f"{len(avg_predictions)} predictions"
            )

        # ── Build sorted results ──
        scored = [
            {"label": label, "confidence": float(avg_predictions[i])}
            for i, label in enumerate(labels)
        ]
        scored.sort(key=lambda x: x["confidence"], reverse=True)

        def parse_label(label: str) -> tuple[str, str]:
            if "---" in label:
                parts = label.split("---", 1)
                return parts[0].strip(), parts[1].strip()
            return label.strip(), ""

        all_genres = [
            {
                "genre": parse_label(item["label"])[0],
                "subgenre": parse_label(item["label"])[1],
                "confidence": round(item["confidence"], 4),
            }
            for item in scored
        ]

        top_genres = [g for g in all_genres if g["confidence"] >= 0.01][:5]

        if top_genres:
            top = top_genres[0]
            print(
                f"[genre_detect] ✅ Top genre: {top['genre']} › {top['subgenre']} "
                f"({round(top['confidence'] * 100, 1)}%)"
            )
        else:
            print("[genre_detect] ⚠️ No genre predicted above 1% confidence threshold")

        return {
            "top_genres": top_genres,
            "all_genres": all_genres[:20],
            "source": "essentia",
        }

    except ImportError:
        print("[genre_detect] ⚠️ Essentia not installed — skipping genre detection")
        print("[genre_detect] Run: pip install essentia-tensorflow")
        return {}
    except FileNotFoundError as e:
        print(f"[genre_detect] ⚠️ Model file not found (non-fatal): {e}")
        return {}
    except Exception as e:
        print(f"[genre_detect] ⚠️ Genre detection failed (non-fatal): {e}")
        return {}