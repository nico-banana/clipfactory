# fal.ai API Reference

> Source: [docs.fal.ai](https://docs.fal.ai/)
> Last updated: 2026-03-04

---

## Authentication

**Method:** API Key via `Authorization` header or environment variable

```bash
export FAL_KEY="your-fal-api-key"
```

Get your key: [fal.ai Dashboard → Keys](https://fal.ai/dashboard/keys)

---

## Python Client Setup

```bash
pip install fal-client
```

```python
import fal_client

# Key is auto-read from FAL_KEY env var
# Or set explicitly:
# fal_client.api_key = "your-key"
```

---

## API Architecture

fal.ai exposes three execution modes:

| Mode | URL | Best For |
|------|-----|----------|
| **Queue** (recommended) | `https://queue.fal.run/{model_id}` | Async — submit job, poll for result |
| **Sync** | `https://fal.run/{model_id}` | Quick tasks that complete fast |
| **WebSocket** | `wss://ws.fal.run/{model_id}` | Real-time streaming |

### Queue Pattern (Recommended)

```python
import fal_client

# subscribe() = submit + auto-poll until done
result = fal_client.subscribe(
    "fal-ai/kling-video/v2.1/standard/image-to-video",
    arguments={
        "image_url": "https://example.com/image.jpg",
        "prompt": "Gentle camera zoom in",
        "duration": "5",
        "aspect_ratio": "9:16"
    }
)
video_url = result["video"]["url"]
```

### Manual Queue (More Control)

```python
import fal_client

# Submit
handler = fal_client.submit(
    "fal-ai/kling-video/v2.1/standard/image-to-video",
    arguments={...}
)

# Check status
status = handler.status()
print(status)  # "IN_QUEUE" or "COMPLETED"

# Get result when done
result = handler.get()
```

### File Upload

```python
url = fal_client.upload_file("path/to/local/image.png")
# Returns a fal CDN URL you can pass to any model
```

---

## Video Generation Models

### Kling 3.0 — O3 (Omni) — Dual-Frame ⭐ Default

Kling O3 supports **start + end frame** interpolation for smooth cinematic transitions.

| Model | Endpoint | Cost/sec |
|-------|----------|:--------:|
| **Kling O3 Standard** | `fal-ai/kling-video/o3/standard/image-to-video` | $0.168 (no audio) / $0.224 (audio) |
| Kling O3 Pro | `fal-ai/kling-video/o3/pro/image-to-video` | ~$0.30+ |
| Kling V3 Pro | `fal-ai/kling-video/v3/pro/image-to-video` | ~$0.30+ |

**API Parameters:**
- `image_url` (required) — Start frame image URL
- `end_image_url` (optional) — End frame image URL
- `prompt` — Motion/style text guidance
- `duration` — 3 to 15 seconds (default: 5)
- `generate_audio` — Native audio generation (boolean)
- `multi_prompt` — Multi-shot storyboarding (advanced)

```python
# Dual-frame animation (O3)
result = fal_client.subscribe(
    "fal-ai/kling-video/o3/standard/image-to-video",
    arguments={
        "image_url": "https://...start-frame.png",
        "end_image_url": "https://...end-frame.png",
        "prompt": "Smooth camera zoom revealing product details",
        "duration": "5",
        "generate_audio": False
    }
)
video_url = result["video"]["url"]
```

### Kling 2.x (via fal.ai)

| Model | Endpoint | Cost/sec |
|-------|----------|:--------:|
| Kling 2.5 Turbo Pro | `fal-ai/kling-video/v2.5-turbo/pro/image-to-video` | ~$0.14 |
| Kling 2.5 Standard | `fal-ai/kling-video/v2.5/standard/image-to-video` | ~$0.07 |
| Kling 2.1 Pro | `fal-ai/kling-video/v2.1/pro/image-to-video` | ~$0.14 |
| Kling 2.1 Standard | `fal-ai/kling-video/v2.1/standard/image-to-video` | ~$0.07 |

```python
result = fal_client.subscribe(
    "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
    arguments={
        "image_url": "https://...",
        "prompt": "Natural subtle movement, person smiling",
        "duration": "5",
        "aspect_ratio": "9:16"
    }
)
```

### Luma Dream Machine (via fal.ai)

| Model | Endpoint |
|-------|----------|
| Luma Dream Machine | `fal-ai/luma-dream-machine` |

```python
result = fal_client.subscribe(
    "fal-ai/luma-dream-machine",
    arguments={
        "prompt": "Cinematic product shot",
        "image_url": "https://...",
        "aspect_ratio": "9:16"
    }
)
```

### Minimax / Hailuo (via fal.ai)

| Model | Endpoint |
|-------|----------|
| Minimax Video | `fal-ai/minimax/video-01` |
| Minimax Live | `fal-ai/minimax/video-01-live` |

### Stable Video Diffusion (via fal.ai)

| Model | Endpoint | Cost |
|-------|----------|:----:|
| SVD | `fal-ai/stable-video` | ~$0.075 flat |

---

## Image Generation Models

| Model | Endpoint | Cost |
|-------|----------|:----:|
| FLUX.1 [schnell] | `fal-ai/flux/schnell` | ~$0.003 |
| FLUX.1 [dev] | `fal-ai/flux/dev` | ~$0.025 |
| FLUX Pro Ultra | `fal-ai/flux-pro/v1.1-ultra` | ~$0.05 |
| Stable Diffusion XL | `fal-ai/fast-sdxl` | ~$0.005 |

```python
result = fal_client.subscribe(
    "fal-ai/flux/schnell",
    arguments={
        "prompt": "A pair of stylish glasses on a marble surface, product photography",
        "image_size": "portrait_16_9",
        "num_images": 1
    }
)
image_url = result["images"][0]["url"]
```

---

## Voice / Audio Models (ElevenLabs via fal.ai)

| Model | Endpoint | Description |
|-------|----------|-------------|
| ElevenLabs TTS | `fal-ai/elevenlabs/tts` | Text-to-Speech |
| ElevenLabs Multilingual v2 | `fal-ai/elevenlabs/tts/multilingual-v2` | 32+ languages |
| ElevenLabs Turbo v2.5 | `fal-ai/elevenlabs/tts/turbo-v2.5` | Low-latency TTS |
| Audio Isolation | `fal-ai/elevenlabs/audio-isolation` | Clean audio |
| Sound Effects | `fal-ai/elevenlabs/sound-effects` | Generate SFX |

```python
result = fal_client.subscribe(
    "fal-ai/elevenlabs/tts/multilingual-v2",
    arguments={
        "text": "Tiesitkö, että optikkoliikkeessä monitehot maksaa 600–800 euroa?",
        "voice_id": "FINNISH_VOICE_ID",
        "model_id": "eleven_multilingual_v2"
    }
)
audio_url = result["audio"]["url"]
```

---

## Common Parameters

### Video Models
| Parameter | Type | Description |
|-----------|------|-------------|
| `image_url` | string | Input image URL |
| `prompt` | string | Motion/action description |
| `duration` | string | "5" or "10" seconds |
| `aspect_ratio` | string | "9:16", "16:9", "1:1" |

### Image Models
| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | string | Image description |
| `image_size` | string | "square_hd", "portrait_16_9", etc. |
| `num_images` | int | Number of images (1-4) |
| `seed` | int | Reproducibility seed |

---

## Model Discovery

Browse all 600+ models: [fal.ai/models](https://fal.ai/models)

Filter by category:
- [Video models](https://fal.ai/models?category=video)
- [Image models](https://fal.ai/models?category=image)
- [Audio models](https://fal.ai/models?category=audio)
- [Voice models](https://fal.ai/models?category=voice)

---

## Pricing Model

fal.ai uses **pure pay-per-use** pricing:
- No subscription required
- Billed per output unit (per second for video, per image for images)
- GPU compute: H100 from $1.89/hour (for custom deployments)

### Cost Examples for ClipFactory
| Action | Model | ~Cost |
|--------|-------|:-----:|
| Generate 1 product image | Nano Banana 2 (Gemini) | ~$0.07 |
| Generate 1 frame pair (start+end) | Nano Banana 2 (Gemini) | ~$0.14 |
| Animate 5s clip (dual-frame) | Kling O3 Standard | ~$0.84 |
| Animate 5s clip (single-frame) | Kling 2.5 Standard | ~$0.35 |
| Generate voiceover | ElevenLabs TTS | $0.01–0.03 |
| Full 7-scene ad (O3 dual-frame) | Mixed | ~$7.00 |
| Full 7-scene ad (legacy single) | Mixed | ~$3.00 |

---

## Error Handling

```python
try:
    result = fal_client.subscribe("fal-ai/kling-video/...", arguments={...})
except fal_client.FalError as e:
    print(f"Error: {e.status_code} - {e.message}")
```

---

## Links
- [Documentation](https://docs.fal.ai/)
- [Model Catalog](https://fal.ai/models)
- [Quickstart](https://docs.fal.ai/model-apis/quickstart)
- [API Reference](https://docs.fal.ai/model-apis/model-endpoints)
- [Python Client](https://docs.fal.ai/model-apis/clients)
- [Dashboard](https://fal.ai/dashboard)
- [Status Page](https://status.fal.ai/)
- [MCP Server](https://docs.fal.ai/model-apis/mcp)
- [Discord](https://discord.gg/fal-ai)
