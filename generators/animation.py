"""
ClipFactory — Animation Module
Animates still images into video clips using fal.ai (Kling, Luma, etc).
"""

import os
import time
import json
import requests
from pathlib import Path

try:
    import fal_client
    HAS_FAL = True
except ImportError:
    HAS_FAL = False
    print("⚠️  fal-client not installed. Run: pip install fal-client")


class AnimationEngine:
    """Animate images into video clips via fal.ai."""

    # Available models on fal.ai for image-to-video
    MODELS = {
        "kling-2.1": "fal-ai/kling-video/v2.1/standard/image-to-video",
        "kling-2.5": "fal-ai/kling-video/v2.5/standard/image-to-video",
        "luma": "fal-ai/luma-dream-machine",
        "minimax": "fal-ai/minimax-video/image-to-video",
        "stable-video": "fal-ai/stable-video",
    }

    def __init__(self, config: dict):
        self.config = config.get("animation", {})
        model_key = self.config.get("model", "fal-ai/kling-video/v2.1/standard/image-to-video")

        # Allow both short keys and full model paths
        if model_key in self.MODELS:
            self.model = self.MODELS[model_key]
        else:
            self.model = model_key

        self.duration = self.config.get("duration", 5)
        self.aspect_ratio = self.config.get("aspect_ratio", "9:16")

        fal_key = os.environ.get("FAL_KEY")
        if not fal_key:
            raise ValueError("FAL_KEY environment variable not set")

        # fal_client uses FAL_KEY env var automatically

    def _upload_image(self, image_path: str) -> str:
        """Upload a local image to fal.ai and return the URL."""
        if not HAS_FAL:
            raise RuntimeError("fal-client library not available")

        print(f"     📤 Uploading image: {os.path.basename(image_path)}")
        url = fal_client.upload_file(image_path)
        return url

    def animate(self, image_path: str, animation_prompt: str,
                output_dir: str, scene_id: int = 0, duration: int = None) -> str:
        """
        Animate a single image into a video clip.
        Returns the path to the saved video.
        """
        if not HAS_FAL:
            raise RuntimeError("fal-client library not available")

        clip_duration = duration or self.duration

        print(f"  🎬 Animating scene {scene_id} ({clip_duration}s)...")
        print(f"     Motion: {animation_prompt[:80]}...")

        try:
            # Upload image to fal.ai
            image_url = self._upload_image(image_path)

            # Build request arguments based on model
            arguments = {
                "image_url": image_url,
                "prompt": animation_prompt,
                "duration": str(clip_duration),
                "aspect_ratio": self.aspect_ratio,
            }

            # Submit and wait for result
            result = fal_client.subscribe(
                self.model,
                arguments=arguments,
                with_logs=True,
                on_queue_update=lambda update: self._on_queue_update(update, scene_id),
            )

            # Download the resulting video
            video_url = None
            if isinstance(result, dict):
                # Different models return video URL in different fields
                video_url = (
                    result.get("video", {}).get("url") or
                    result.get("video_url") or
                    result.get("output", {}).get("url") if isinstance(result.get("output"), dict) else None
                )
                # Try nested structures
                if not video_url and "video" in result:
                    if isinstance(result["video"], str):
                        video_url = result["video"]

            if not video_url:
                print(f"  ⚠️  Unexpected response structure: {json.dumps(result, indent=2)[:500]}")
                raise RuntimeError("Could not find video URL in response")

            # Download video
            output_path = f"{output_dir}/clips"
            Path(output_path).mkdir(parents=True, exist_ok=True)
            file_path = f"{output_path}/scene_{scene_id:02d}.mp4"

            print(f"     📥 Downloading video...")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"  ✅ Clip saved: {file_path}")
            return file_path

        except Exception as e:
            print(f"  ❌ Animation failed for scene {scene_id}: {e}")
            raise

    def _on_queue_update(self, update, scene_id):
        """Handle queue status updates from fal.ai."""
        if hasattr(update, 'status'):
            if update.status == "IN_QUEUE":
                print(f"     ⏳ Scene {scene_id}: In queue...")
            elif update.status == "IN_PROGRESS":
                print(f"     🔄 Scene {scene_id}: Processing...")

    def animate_batch(self, scenes: list, image_results: list,
                      output_dir: str) -> list:
        """
        Animate all scenes that have generated images.

        Args:
            scenes: List of scene dicts from script
            image_results: List of (scene_id, image_path) from image generation
            output_dir: Base output directory

        Returns:
            List of (scene_id, clip_path) tuples
        """
        # Build lookup from scene_id to image_path
        image_lookup = {sid: path for sid, path in image_results if path is not None}
        results = []
        total = len(image_lookup)

        print(f"\n🎬 Animating {total} scenes...")
        print(f"   Model: {self.model}")
        print(f"   Duration: {self.duration}s per clip\n")

        for scene in scenes:
            scene_id = scene.get("scene_id")
            image_path = image_lookup.get(scene_id)

            if not image_path:
                print(f"  ⏭️  Scene {scene_id}: No image available, skipping")
                continue

            animation_prompt = scene.get("animation_prompt", "Gentle cinematic movement")
            duration = scene.get("duration", self.duration)

            try:
                clip_path = self.animate(
                    image_path=image_path,
                    animation_prompt=animation_prompt,
                    output_dir=output_dir,
                    scene_id=scene_id,
                    duration=duration,
                )
                results.append((scene_id, clip_path))

                # Rate limiting between animations
                time.sleep(1)

            except Exception as e:
                print(f"  ❌ Scene {scene_id} animation failed: {e}")
                results.append((scene_id, None))

        successful = sum(1 for _, path in results if path is not None)
        print(f"\n📊 Animation complete: {successful}/{total} successful")

        return results
