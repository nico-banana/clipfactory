# 🏭 ClipFactory

Automated ad clip generation pipeline — script in, clips out.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API keys
export GEMINI_API_KEY="your-google-ai-studio-key"
export FAL_KEY="your-fal-ai-key"

# 3. Run the pipeline
python clipfactory.py scripts/banaani-ugc-01.json
```

## Usage

```bash
# Full pipeline (images → animation → assembly)
python clipfactory.py scripts/banaani-ugc-01.json

# Images only (test image generation first)
python clipfactory.py scripts/banaani-ugc-01.json --images-only

# Animate existing images
python clipfactory.py scripts/banaani-ugc-01.json --animate-only

# Single scene (for testing)
python clipfactory.py scripts/banaani-ugc-01.json --scene 1

# Skip final assembly
python clipfactory.py scripts/banaani-ugc-01.json --skip-assembly
```

## Project Structure

```
clipfactory/
├── clipfactory.py          # Main orchestrator
├── generators/
│   ├── image_gen.py        # Nano Banana 2 (Gemini API)
│   └── animation.py        # fal.ai (Kling, Luma, etc.)
├── assembler.py            # FFmpeg clip stitching
├── scripts/                # Input scripts (JSON)
│   └── banaani-ugc-01.json
├── output/                 # Generated clips (gitignored)
├── config.yaml             # Model & output settings
├── requirements.txt        # Python dependencies
└── README.md
```

## Script Format

Scripts are JSON files that define the ad flow:

```json
{
  "project": "banaani-ugc-01",
  "client": "banaani",
  "aspect_ratio": "9:16",
  "scenes": [
    {
      "scene_id": 1,
      "duration": 5,
      "image_prompt": "Description for image generation...",
      "animation_prompt": "How the image should move...",
      "text_overlay": "Optional text on screen",
      "voiceover_text": "What is being said"
    }
  ]
}
```

## API Keys

| Service | Get Key | Cost |
|---------|---------|------|
| Google AI Studio | [aistudio.google.com](https://aistudio.google.com) | ~$0.07/image |
| fal.ai | [fal.ai/dashboard](https://fal.ai/dashboard) | ~$0.35/5s clip |

## Configuration

Edit `config.yaml` to change models, resolution, or output settings.

### Available animation models (via fal.ai):
- `kling-2.1` — Kling v2.1 (default, good balance)
- `kling-2.5` — Kling v2.5 (latest, best quality)
- `luma` — Luma Dream Machine (cinematic)
- `minimax` — Minimax (fast)
- `stable-video` — Stable Video ($0.075/vid, cheapest)
