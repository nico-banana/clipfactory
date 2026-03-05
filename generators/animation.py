"""
ClipFactory — Animation Module
Animates still images into video clips using fal.ai.
Supports Kling O3 dual-frame (start + end) interpolation for smooth transitions.
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
        # Kling 3.0 series
        "kling-o3-standard": "fal-ai/kling-video/o3/standard/image-to-video",
        "kling-o3-pro": "fal-ai/kling-video/o3/pro/image-to-video",
        "kling-v3-pro": "fal-ai/kling-video/v3/pro/image-to-video",
        # Kling 2.x series
        "kling-2.5-turbo-pro": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
        "kling-2.5": "fal-ai/kling-video/v2.5/standard/image-to-video",
        "kling-2.1": "fal-ai/kling-video/v2.1/standard/image-to-video",
        "kling-2.1-pro": "fal-ai/kling-video/v2.1/pro/image-to-video",
        # Other models
        "veo-3.1": "fal-ai/veo3.1/image-to-video",
        "luma": "fal-ai/luma-dream-machine",
        "minimax": "fal-ai/minimax-video/image-to-video",
        "pixverse-v5": "fal-ai/pixverse/v5/image-to-video",
        "stable-video": "fal-ai/stable-video",
    }

    # Models that support dual-frame (start + end image)
    DUAL_FRAME_MODELS = {
        "fal-ai/kling-video/o3/standard/image-to-video",
        "fal-ai/kling-video/o3/pro/image-to-video",
    }

    def __init__(self, config: dict):
        self.config = config.get("animation", {})
        model_key = self.config.get("model", "fal-ai/kling-video/o3/standard/image-to-video")

        # Allow both short keys and full model paths
        if model_key in self.MODELS:
            self.model = self.MODELS[model_key]
        else:
            self.model = model_key

        self.duration = self.config.get("duration", 5)
        self.aspect_ratio = self.config.get("aspect_ratio", "9:16")
        self.generate_audio = self.config.get("generate_audio", False)

        # Check if this model supports dual-frame
        self.supports_dual_frame = self.model in self.DUAL_FRAME_MODELS

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
                output_dir: str, scene_id: int = 0, duration: int = None,
                end_image_path: str = None) -> str:
        """
        Animate image(s) into a video clip.

        For O3 models: supports start frame + end frame for smooth interpolation.
        For other models: uses single image as before.

        Returns the path to the saved video.
        """
        if not HAS_FAL:
            raise RuntimeError("fal-client library not available")

        clip_duration = duration or self.duration
        has_end_frame = end_image_path is not None and self.supports_dual_frame

        mode = "dual-frame" if has_end_frame else "single-frame"
        print(f"  🎬 Animating scene {scene_id} ({clip_duration}s, {mode})...")
        print(f"     Motion: {animation_prompt[:80]}...")

        try:
            # Upload start image
            image_url = self._upload_image(image_path)

            # Build request arguments
            arguments = {
                "image_url": image_url,
                "prompt": animation_prompt,
                "duration": str(clip_duration),
            }

            # Upload and add end frame if available (O3 models)
            if has_end_frame:
                end_image_url = self._upload_image(end_image_path)
                arguments["end_image_url"] = end_image_url
                print(f"     🔗 End frame attached for smooth transition")

            # Add aspect ratio (for non-O3 models)
            if not self.supports_dual_frame:
                arguments["aspect_ratio"] = self.aspect_ratio

            # Add audio generation flag (O3 models)
            if self.supports_dual_frame and self.generate_audio:
                arguments["generate_audio"] = True

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
                    result.get("video", {}).get("url")
                    or result.get("video_url")
                    or (result.get("output", {}).get("url") if isinstance(result.get("output"), dict) else None)
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
            image_results: List of (scene_id, start_path, end_path) tuples
                           OR legacy (scene_id, image_path) tuples
            output_dir: Base output directory

        Returns:
            List of (scene_id, clip_path) tuples
        """
        # Normalize to (scene_id, start_path, end_path) format
        normalized = []
        for item in image_results:
            if len(item) == 2:
                # Legacy format: (scene_id, path)
                normalized.append((item[0], item[1], None))
            elif len(item) == 3:
                # New format: (scene_id, start_path, end_path)
                normalized.append(item)

        # Build lookup from scene_id to (start_path, end_path)
        image_lookup = {
            sid: (start, end)
            for sid, start, end in normalized
            if start is not None
        }
        total = len(image_lookup)

        dual_count = sum(1 for _, (_, end) in image_lookup.items() if end)
        mode = f"{dual_count} dual-frame, {total - dual_count} single-frame"

        print(f"\n🎬 Animating {total} scenes in parallel...")
        print(f"   Model: {self.model}")
        print(f"   Mode:  {mode}")
        print(f"   Duration: {self.duration}s per clip\n")

        # ─── Submit all jobs concurrently ───
        jobs = {}  # scene_id -> (handle, metadata)

        for scene in scenes:
            scene_id = scene.get("scene_id") or scene.get("clip_id")
            paths = image_lookup.get(scene_id)

            if not paths:
                print(f"  ⏭️  Scene {scene_id}: No image available, skipping")
                continue

            start_path, end_path = paths
            animation_prompt = scene.get("motion_prompt") or scene.get("animation_prompt", "Gentle cinematic movement")
            duration = scene.get("duration", self.duration)
            has_end_frame = end_path is not None and self.supports_dual_frame

            try:
                # Upload images
                image_url = self._upload_image(start_path)

                arguments = {
                    "image_url": image_url,
                    "prompt": animation_prompt,
                    "duration": str(duration),
                }

                if has_end_frame:
                    end_image_url = self._upload_image(end_path)
                    arguments["end_image_url"] = end_image_url

                if not self.supports_dual_frame:
                    arguments["aspect_ratio"] = self.aspect_ratio

                if self.supports_dual_frame and self.generate_audio:
                    arguments["generate_audio"] = True

                # Submit (non-blocking)
                handle = fal_client.submit(self.model, arguments=arguments)
                jobs[scene_id] = (handle, duration, has_end_frame)
                print(f"  🚀 Scene {scene_id} submitted ({duration}s, {'dual' if has_end_frame else 'single'})")

            except Exception as e:
                print(f"  ❌ Scene {scene_id} submit failed: {e}")

        print(f"\n  ⏳ {len(jobs)} jobs submitted, waiting for results...\n")

        # ─── Wait for all jobs (each handle.get() blocks until done) ───
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _wait_and_download(scene_id, handle, output_dir):
            """Block on handle.get(), extract URL, download video."""
            try:
                result = handle.get()

                # Extract video URL
                video_url = None
                if isinstance(result, dict):
                    video_url = (
                        result.get("video", {}).get("url")
                        or result.get("video_url")
                        or (result.get("output", {}).get("url") if isinstance(result.get("output"), dict) else None)
                    )
                    if not video_url and "video" in result:
                        if isinstance(result["video"], str):
                            video_url = result["video"]

                if not video_url:
                    print(f"  ❌ Scene {scene_id}: No video URL in response")
                    return (scene_id, None)

                # Download video
                clip_dir = f"{output_dir}/clips"
                Path(clip_dir).mkdir(parents=True, exist_ok=True)
                file_path = f"{clip_dir}/scene_{scene_id:02d}.mp4"

                response = requests.get(video_url, stream=True)
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"  ✅ Scene {scene_id} done → {os.path.basename(file_path)}")
                return (scene_id, file_path)

            except Exception as e:
                print(f"  ❌ Scene {scene_id} failed: {e}")
                return (scene_id, None)

        results = []
        with ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            futures = {
                executor.submit(_wait_and_download, sid, handle, output_dir): sid
                for sid, (handle, dur, dual) in jobs.items()
            }
            for future in as_completed(futures):
                results.append(future.result())

        # Sort results by scene_id
        results.sort(key=lambda x: x[0])

        successful = sum(1 for _, path in results if path is not None)
        print(f"\n📊 Animation complete: {successful}/{total} successful (parallel)")

        return results

