"""
ClipFactory — ElevenLabs Voiceover Generator with SRT

Generates voiceover audio + SRT subtitle files from script text.
Supports multiple variants per scene for review before proceeding.
"""

import os
import json
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Finnish TTS text patterns that need preprocessing
import re

def preprocess_finnish_tts(text: str) -> str:
    """
    Preprocess Finnish text for TTS to handle symbols and patterns
    that speech synthesis reads incorrectly.
    """
    # Number ranges: "600 - 800" → "600 viiva 800"
    text = re.sub(r'(\d+)\s*[-–—]\s*(\d+)', r'\1 viiva \2', text)
    
    # Percentage: "50%" → "50 prosenttia"
    text = re.sub(r'(\d+)\s*%', r'\1 prosenttia', text)
    
    # Euro symbol: "100€" → "100 euroa"
    text = re.sub(r'(\d+)\s*€', r'\1 euroa', text)
    
    # Euro symbol before: "€100" → "100 euroa"
    text = re.sub(r'€\s*(\d+)', r'\1 euroa', text)
    
    # Plus sign in context: "+10" → "plus 10"
    text = re.sub(r'\+(\d+)', r'plus \1', text)
    
    # Slash: "24/7" → "24 7"
    text = re.sub(r'(\d+)/(\d+)', r'\1 \2', text)
    
    return text


def generate_voiceover(
    text: str,
    voice_id: str,
    output_dir: str,
    filename_prefix: str = "voiceover",
    model_id: str = "eleven_multilingual_v2",
    variants: int = 1,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
) -> list[dict]:
    """
    Generate voiceover audio + SRT file from text.
    
    Args:
        text: The voiceover script text
        voice_id: ElevenLabs voice ID
        output_dir: Directory to save files
        filename_prefix: Base filename (e.g., scene_01)
        model_id: ElevenLabs model (eleven_multilingual_v2 for Finnish)
        variants: Number of variants to generate
        stability: Voice stability (0-1, lower = more varied)
        similarity_boost: Voice similarity (0-1)
        style: Style exaggeration (0-1)
    
    Returns:
        List of dicts with audio_path, srt_path, and duration
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not set in environment")

    # Preprocess Finnish text for TTS
    text = preprocess_finnish_tts(text)

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for v in range(1, variants + 1):
        suffix = f"_v{v}" if variants > 1 else ""
        audio_path = os.path.join(output_dir, f"{filename_prefix}{suffix}.mp3")
        srt_path = os.path.join(output_dir, f"{filename_prefix}{suffix}.srt")

        # Generate with timestamps
        audio_data, timestamps = _call_elevenlabs_with_timestamps(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
        )

        # Save audio
        with open(audio_path, "wb") as f:
            f.write(audio_data)

        # Generate and save SRT
        srt_content = _timestamps_to_srt(timestamps, text)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        duration = timestamps[-1]["end"] if timestamps else 0

        results.append({
            "audio_path": audio_path,
            "srt_path": srt_path,
            "duration": round(duration, 2),
            "variant": v,
        })

        print(f"  ✅ Variant {v}: {audio_path} ({duration:.1f}s)")
        print(f"     SRT: {srt_path}")

    return results


def _call_elevenlabs_with_timestamps(
    text: str,
    voice_id: str,
    model_id: str,
    stability: float,
    similarity_boost: float,
    style: float,
) -> tuple[bytes, list]:
    """Call ElevenLabs API with timestamp alignment."""
    
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}/with-timestamps"

    payload = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())

    # Decode base64 audio
    import base64
    audio_bytes = base64.b64decode(data["audio_base64"])

    # Extract word-level timestamps
    alignment = data.get("alignment", {})
    characters = alignment.get("characters", [])
    char_starts = alignment.get("character_start_times_seconds", [])
    char_ends = alignment.get("character_end_times_seconds", [])

    # Group characters into words with timestamps
    words = _chars_to_words(characters, char_starts, char_ends)

    return audio_bytes, words


def _chars_to_words(characters: list, starts: list, ends: list) -> list:
    """Group character-level timestamps into word-level timestamps."""
    words = []
    current_word = ""
    word_start = 0

    for i, char in enumerate(characters):
        if char == " " or i == len(characters) - 1:
            if i == len(characters) - 1 and char != " ":
                current_word += char

            if current_word.strip():
                words.append({
                    "word": current_word.strip(),
                    "start": word_start,
                    "end": ends[i - 1] if char == " " else ends[i],
                })

            current_word = ""
            if i + 1 < len(starts):
                word_start = starts[i + 1]
        else:
            if not current_word:
                word_start = starts[i]
            current_word += char

    return words


def _timestamps_to_srt(words: list, original_text: str, words_per_line: int = 5) -> str:
    """Convert word timestamps to SRT subtitle format."""
    if not words:
        return ""

    srt_lines = []
    idx = 1

    for i in range(0, len(words), words_per_line):
        chunk = words[i : i + words_per_line]
        start_time = chunk[0]["start"]
        end_time = chunk[-1]["end"]
        text = " ".join(w["word"] for w in chunk)

        srt_lines.append(f"{idx}")
        srt_lines.append(f"{_format_srt_time(start_time)} --> {_format_srt_time(end_time)}")
        srt_lines.append(text)
        srt_lines.append("")
        idx += 1

    return "\n".join(srt_lines)


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_scene_voiceovers(
    script: dict,
    output_dir: str,
    voice_id: str = None,
    variants: int = 3,
) -> dict:
    """
    Generate voiceovers for all scenes in a script that have voiceover_text.
    
    Args:
        script: Parsed script JSON
        output_dir: Base output directory
        voice_id: Override voice ID (uses script default if not provided)
        variants: Number of variants per scene
    
    Returns:
        Dict mapping scene index to list of generated files
    """
    voice_id = voice_id or script.get("avatar", {}).get("voice_id")
    if not voice_id:
        raise ValueError("No voice_id provided or found in script")

    vo_dir = os.path.join(output_dir, "voiceovers")
    results = {}

    scenes = script.get("scenes", [])
    for i, scene in enumerate(scenes):
        vo_text = scene.get("voiceover_text")
        if not vo_text:
            print(f"  ⏭️  Scene {i + 1}: No voiceover text, skipping")
            continue

        print(f"\n🎤 Scene {i + 1}: \"{vo_text[:60]}...\"")
        scene_results = generate_voiceover(
            text=vo_text,
            voice_id=voice_id,
            output_dir=vo_dir,
            filename_prefix=f"scene_{i + 1:02d}",
            variants=variants,
        )
        results[i] = scene_results

    print(f"\n✅ Generated voiceovers for {len(results)} scenes")
    print(f"📁 Files saved to: {vo_dir}")
    return results


# --- CLI ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate voiceovers with SRT")
    parser.add_argument("script", help="Path to script JSON file")
    parser.add_argument("--voice-id", default="dwKzSSwRu0m7qSpdvqwk",
                        help="ElevenLabs voice ID")
    parser.add_argument("--variants", type=int, default=3,
                        help="Number of variants per scene")
    parser.add_argument("--output", default="output",
                        help="Output directory")
    parser.add_argument("--scene", type=int, default=None,
                        help="Generate for a single scene only")
    parser.add_argument("--text", type=str, default=None,
                        help="Generate a single voiceover from text (ignores script)")
    args = parser.parse_args()

    if args.text:
        # Quick single voiceover test
        print(f"🎤 Generating voiceover: \"{args.text[:60]}...\"")
        results = generate_voiceover(
            text=args.text,
            voice_id=args.voice_id,
            output_dir=args.output,
            filename_prefix="test",
            variants=args.variants,
        )
    else:
        with open(args.script) as f:
            script = json.load(f)

        if args.scene is not None:
            # Single scene
            scene = script["scenes"][args.scene - 1]
            vo_text = scene.get("voiceover_text")
            if not vo_text:
                print(f"Scene {args.scene} has no voiceover text")
                exit(1)
            print(f"🎤 Scene {args.scene}: \"{vo_text[:60]}...\"")
            generate_voiceover(
                text=vo_text,
                voice_id=args.voice_id,
                output_dir=os.path.join(args.output, "voiceovers"),
                filename_prefix=f"scene_{args.scene:02d}",
                variants=args.variants,
            )
        else:
            generate_scene_voiceovers(
                script=script,
                output_dir=args.output,
                voice_id=args.voice_id,
                variants=args.variants,
            )
