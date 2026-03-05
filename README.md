# 🏭 ClipFactory

Automated ad clip generation pipeline — script in, clips out.

Uses **Kling O3 dual-frame animation** for smooth, cinematic scene transitions.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API keys
cp .env.example .env
# Edit .env with your keys

# 3. Run the pipeline
python clipfactory.py scripts/banaani-ugc-01.json
```

## MCP Workflow (Recommended)

The **fal.ai MCP server** enables running the pipeline directly from AI conversation — no terminal needed. This is the preferred method when working with an AI assistant.

Available tools: `generate_image`, `generate_video_from_image`, `generate_video`, `remove_background`, `upscale_image`, `upload_file`, `list_models`, `get_pricing`.

See `/clipfactory` workflow for full instructions.

## Usage (Script Mode)

```bash
# Full pipeline (images → animation → assembly)
python clipfactory.py scripts/banaani-ugc-03.json

# Images only (test image generation first)
python clipfactory.py scripts/banaani-ugc-03.json --images-only

# Animate existing images
python clipfactory.py scripts/banaani-ugc-03.json --animate-only

# Single scene (for testing)
python clipfactory.py scripts/banaani-ugc-03.json --scene 1

# Skip final assembly
python clipfactory.py scripts/banaani-ugc-03.json --skip-assembly
```

## Project Structure

```
clipfactory/
├── clipfactory.py          # Main orchestrator
├── generators/
│   ├── image_gen.py        # Nano Banana 2 (Gemini API) — dual-frame support
│   ├── animation.py        # fal.ai (Kling O3, Kling 2.5, Luma, etc.)
│   └── voiceover.py        # ElevenLabs Finnish voiceovers
├── assembler.py            # FFmpeg clip stitching
├── scripts/                # Input scripts (JSON)
│   └── banaani-ugc-03.json # Example: dual-frame B-roll script
├── output/                 # Generated clips (gitignored)
├── docs/                   # API reference docs
├── config.yaml             # Model & output settings
├── requirements.txt        # Python dependencies
└── README.md
```

## Script Format

### Dual-Frame (Kling O3) — Recommended

Each B-roll clip gets a **start frame** and **end frame**. Kling O3 smoothly interpolates between them:

```json
{
  "project": "my-ad-01",
  "client": "acme",
  "aspect_ratio": "9:16",
  "broll_clips": [
    {
      "clip_id": 1,
      "timing": "0-3s",
      "start_image_prompt": "Product on table, wide shot...",
      "end_image_prompt": "Close-up of the same product showing details...",
      "motion_prompt": "Smooth camera zoom towards product details",
      "reference_image": null
    }
  ]
}
```

### Single-Frame (Legacy)

Still supported for backward compatibility:

```json
{
  "project": "my-ad-01",
  "client": "acme",
  "scenes": [
    {
      "scene_id": 1,
      "duration": 5,
      "image_prompt": "Product shot description...",
      "animation_prompt": "How the image should move...",
      "text_overlay": "Optional text on screen"
    }
  ]
}
```

## Available Animation Models

| Model | Key | Best For | Cost/5s |
|-------|-----|----------|:-------:|
| **Kling O3 Standard** | `kling-o3-standard` | Dual-frame, smooth transitions | ~$0.84 |
| Kling O3 Pro | `kling-o3-pro` | Premium dual-frame | ~$1.50 |
| Kling V3 Pro | `kling-v3-pro` | Best single-frame cinematic | ~$1.50 |
| Kling 2.5 Turbo Pro | `kling-2.5-turbo-pro` | Fast + high quality | ~$0.70 |
| Kling 2.5 Standard | `kling-2.5` | Budget option | ~$0.35 |
| Veo 3.1 | `veo-3.1` | Google DeepMind | ~$0.50–$1.75 |

Set the model in `config.yaml`:

```yaml
animation:
  model: "fal-ai/kling-video/o3/standard/image-to-video"
```

## API Keys

| Service | Get Key | Used For |
|---------|---------|----------|
| Google AI Studio | [aistudio.google.com](https://aistudio.google.com) | Image generation |
| fal.ai | [fal.ai/dashboard](https://fal.ai/dashboard) | Video animation |
| ElevenLabs | [elevenlabs.io](https://elevenlabs.io) | Voiceovers (optional) |
| HeyGen | [heygen.com](https://heygen.com) | Avatar talking heads (optional) |

## Configuration

Edit `config.yaml` to change models, resolution, or output settings.
