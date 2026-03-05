"""
ClipFactory — Image Generator Module
Generates images from text prompts using Nano Banana 2 (Gemini API).
Supports dual-frame generation for Kling O3 (start + end frame).
"""

import os
import base64
import json
import time
from pathlib import Path

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    print("⚠️  google-genai not installed. Run: pip install google-genai")


class ImageGenerator:
    """Generate images via Gemini API (Nano Banana 2)."""

    def __init__(self, config: dict):
        self.config = config.get("image_generation", {})
        self.model = self.config.get("model", "gemini-2.0-flash-exp")
        self.resolution = self.config.get("resolution", "1024x1024")

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        if HAS_GENAI:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def generate(self, prompt: str, output_path: str, scene_id: int = 0,
                 suffix: str = "") -> str:
        """
        Generate a single image from a text prompt.
        Returns the path to the saved image.

        Args:
            prompt: Text prompt for image generation
            output_path: Directory to save the image
            scene_id: Scene number for naming
            suffix: Optional suffix for filename (e.g., '_start', '_end')
        """
        if not self.client:
            raise RuntimeError("google-genai library not available")

        label = f"scene {scene_id}"
        if suffix:
            label += f" ({suffix.strip('_')} frame)"

        print(f"  🎨 Generating image for {label}...")
        print(f"     Prompt: {prompt[:80]}...")

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=1.0,
                ),
            )

            # Extract image from response
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    # Determine file extension
                    ext = part.inline_data.mime_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"

                    file_path = f"{output_path}/scene_{scene_id:02d}{suffix}.{ext}"
                    Path(output_path).mkdir(parents=True, exist_ok=True)

                    with open(file_path, "wb") as f:
                        f.write(part.inline_data.data)

                    print(f"  ✅ Image saved: {file_path}")
                    image_saved = True
                    return file_path

            if not image_saved:
                # Check if there's text response (error or refusal)
                for part in response.candidates[0].content.parts:
                    if part.text:
                        print(f"  ⚠️  Model returned text instead of image: {part.text[:200]}")
                raise RuntimeError("No image generated — model did not return image data")

        except Exception as e:
            print(f"  ❌ Image generation failed for {label}: {e}")
            raise

    def generate_pair(self, start_prompt: str, end_prompt: str,
                      output_dir: str, scene_id: int = 0) -> tuple:
        """
        Generate a start + end frame pair for Kling O3 dual-frame animation.
        Returns (start_image_path, end_image_path).
        """
        output_path = f"{output_dir}/images"

        print(f"\n  🖼️  Generating frame pair for scene {scene_id}...")

        start_path = self.generate(
            prompt=start_prompt,
            output_path=output_path,
            scene_id=scene_id,
            suffix="_start",
        )

        # Rate limiting between generations
        time.sleep(2)

        end_path = self.generate(
            prompt=end_prompt,
            output_path=output_path,
            scene_id=scene_id,
            suffix="_end",
        )

        return start_path, end_path

    def generate_batch(self, scenes: list, output_dir: str,
                       scene_key: str = "scenes") -> list:
        """
        Generate images for all scenes in a script.
        Supports both single-frame (legacy) and dual-frame (O3) formats.

        Returns list of (scene_id, start_path, end_path) tuples.
        end_path is None for single-frame scenes.
        """
        results = []
        total = len(scenes)

        # Detect format: broll_clips use start/end, legacy scenes use image_prompt
        has_dual = any(
            s.get("start_image_prompt") for s in scenes
        )

        mode = "dual-frame (O3)" if has_dual else "single-frame (legacy)"
        print(f"\n🖼️  Generating {total} {'frame pairs' if has_dual else 'images'}...")
        print(f"   Model: {self.model}")
        print(f"   Mode:  {mode}")
        print(f"   Resolution: {self.resolution}\n")

        for i, scene in enumerate(scenes):
            # Support both scene_id and clip_id naming
            scene_id = scene.get("scene_id") or scene.get("clip_id", i + 1)

            start_prompt = scene.get("start_image_prompt") or scene.get("image_prompt", "")
            end_prompt = scene.get("end_image_prompt")

            if not start_prompt:
                print(f"  ⏭️  Scene {scene_id}: No image prompt, skipping")
                results.append((scene_id, None, None))
                continue

            try:
                if end_prompt:
                    # Dual-frame mode (O3)
                    start_path, end_path = self.generate_pair(
                        start_prompt=start_prompt,
                        end_prompt=end_prompt,
                        output_dir=output_dir,
                        scene_id=scene_id,
                    )
                    results.append((scene_id, start_path, end_path))
                else:
                    # Single-frame mode (legacy / backward compatible)
                    image_path = self.generate(
                        prompt=start_prompt,
                        output_path=f"{output_dir}/images",
                        scene_id=scene_id,
                    )
                    results.append((scene_id, image_path, None))

                # Rate limiting between scenes
                if i < total - 1:
                    time.sleep(2)

            except Exception as e:
                print(f"  ❌ Scene {scene_id} failed: {e}")
                results.append((scene_id, None, None))

        successful = sum(1 for _, sp, _ in results if sp is not None)
        print(f"\n📊 Image generation complete: {successful}/{total} successful")

        return results
