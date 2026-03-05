# HeyGen API Reference

> Source: [docs.heygen.com](https://docs.heygen.com/docs/quick-start)
> Last updated: 2026-03-04

---

## Authentication

**Method:** API Key via `X-Api-Key` header

```
X-Api-Key: YOUR_HEYGEN_API_KEY
```

Get your key: [HeyGen Dashboard → Settings → API](https://app.heygen.com/avatar?from=avatar&nav=API)

> [!IMPORTANT]
> HeyGen has **two separate credit pools**: Web plan premium credits (for MCP/OAuth) and API dashboard balance (for API key usage). They don't share credits.

---

## Integration Paths

### 1. Video Agent (Prompt → Video) ⭐ Fastest

One prompt → one complete video. No avatar or template setup needed.

**Endpoint:** `POST https://api.heygen.com/v1/video_agent/generate`

```bash
curl -X POST "https://api.heygen.com/v1/video_agent/generate" \
  -H "X-API-KEY: $HEYGEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A presenter explaining our product launch in 30 seconds"}'
```

**Python:**
```python
import requests

response = requests.post(
    "https://api.heygen.com/v1/video_agent/generate",
    headers={
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "prompt": "A young Finnish woman enthusiastically reviewing glasses, speaking Finnish, casual UGC style"
    }
)
video_id = response.json()["data"]["video_id"]
```

### 2. Avatar Video (Avatar ID + Script → Video)

More control — choose specific avatar, voice, background.

**Flow:**
1. Create or select an avatar → get `avatar_id`
2. Select a voice → get `voice_id`
3. Generate video with script

**Endpoint:** `POST https://api.heygen.com/v2/video/generate`

```python
import requests

response = requests.post(
    "https://api.heygen.com/v2/video/generate",
    headers={
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": "YOUR_AVATAR_ID",
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "input_text": "Tiesitkö, että optikkoliikkeessä monitehot maksaa 600–800 euroa?",
                "voice_id": "FINNISH_VOICE_ID"
            },
            "background": {
                "type": "color",
                "value": "#FFFFFF"
            }
        }],
        "dimension": {
            "width": 1080,
            "height": 1920
        },
        "aspect_ratio": "9:16"
    }
)
video_id = response.json()["data"]["video_id"]
```

### 3. Video Translate (Video → Translated Video)

Translate existing video to another language with lip sync.

**Endpoint:** `POST https://api.heygen.com/v1/video_translate/translate`

---

## API Endpoints Overview

### Video Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/video_agent/generate` | One-shot prompt → video |

### Text to Speech
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/text_to_speech` | Text-to-Speech (Starfish) |
| GET | `/v1/text_to_speech/voices` | List compatible voices |

### Video Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/video/generate` | Create avatar video (Avatar III/IV) |
| GET | `/v1/video_status.get?video_id={id}` | Get video status/details |
| POST | `/v2/video/generate/webm` | Create WebM video (transparent bg) |

### Photo Avatar
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/photo_avatar/photo/generate` | Create photo avatar from prompt |
| POST | `/v2/photo_avatar/group` | Create avatar group |
| POST | `/v2/photo_avatar/group/{id}/looks` | Add looks to group |
| POST | `/v2/photo_avatar/looks/generate` | Generate avatar looks |
| GET | `/v2/photo_avatar/generation_status` | Check generation status |
| GET | `/v2/photo_avatar/{id}` | Get avatar details |
| POST | `/v2/photo_avatar/group/{id}/train` | Train avatar group |
| POST | `/v2/photo_avatar/{id}/motion` | Add motion to avatar |

### Digital Twin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v2/video_avatar` | Create digital twin |
| GET | `/v2/video_avatar/{id}/status` | Check generation status |
| DELETE | `/v2/video_avatar/{id}` | Delete digital twin |

### Video Translate
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/video_translate/translate` | Translate video |
| GET | `/v1/video_translate/languages` | List supported languages |
| GET | `/v1/video_translate/{id}/status` | Get translation status |
| POST | `/v1/video_translate/proofread` | Generate proofread |
| POST | `/v1/video_translate/proofread/generate` | Generate from proofread |

### Voice Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v2/voices` | List all voices |
| GET | `/v2/voices/locales` | List all locales |
| GET | `/v2/brand_voice` | List brand glossary |
| POST | `/v2/brand_voice` | Update brand glossary |

### Avatar Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v2/avatars` | List all avatars |
| GET | `/v2/avatar_groups` | List all avatar groups |
| GET | `/v2/avatar_group/{id}/avatars` | List avatars in group |
| GET | `/v2/avatar/{id}` | Get avatar details |

### Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/asset` | Upload asset (image/video) |
| GET | `/v1/asset` | List assets |
| POST | `/v1/asset/delete` | Delete asset |

### Webhook
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/webhook/endpoint.add` | Add webhook URL |
| GET | `/v1/webhook/endpoint.list` | List webhooks |
| DELETE | `/v1/webhook/endpoint.delete` | Delete webhook |

---

## Pricing

| Plan | Cost/mo | Credits | Cost/Credit | Notes |
|------|:-------:|:-------:|:-----------:|-------|
| Free API | $0 | 10 | — | Watermarked output |
| Pro API | $99 | 100 | ~$0.99 | No watermark, all avatars |
| Scale API | $330 | 660 | ~$0.50 | + Video Translate, proofreading |
| Enterprise | Custom | Custom | Custom | Digital twins via API, dedicated support |

---

## Key Features for ClipFactory

### What HeyGen does that others don't:
1. **Video Agent** — one prompt, one complete video (no avatar setup needed)
2. **Photo Avatar** — generate realistic avatars from text prompts
3. **Digital Twin** — clone a real person into an avatar
4. **Built-in TTS** — native text-to-speech (Starfish engine)
5. **WebM export** — transparent background for compositing
6. **Video Translate** — auto-translate + lip sync to other languages
7. **Brand Glossary** — consistent brand voice across videos

### Recommended ClipFactory Integration:
```python
# Scene type: "talking_head"
# → Route to HeyGen API
# → Use Photo Avatar or Digital Twin
# → Pass voiceover script text
# → Get back video clip with talking avatar
# → Merge with product shots via FFmpeg
```

---

## Links
- [Quick Start](https://docs.heygen.com/docs/quick-start)
- [API Reference](https://docs.heygen.com/reference)
- [Postman Collection](https://docs.heygen.com/reference/postman-collections)
- [Limits & Pricing](https://docs.heygen.com/reference/limits)
- [Authentication Methods](https://docs.heygen.com/docs/authentication-methods)
- [HeyGen Dashboard](https://app.heygen.com/avatar?from=avatar&nav=API)
