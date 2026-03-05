"""
ClipFactory — Image Generator Module
Generates images from text prompts using Nano Banana 2 (Gemini API).
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

    def generate(self, prompt: str, output_path: str, scene_id: int = 0) -> str:
        """
        Generate a single image from a text prompt.
        Returns the path to the saved image.
        """
        if not self.client:
            raise RuntimeError("google-genai library not available")

        print(f"  🎨 Generating image for scene {scene_id}...")
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

                    file_path = f"{output_path}/scene_{scene_id:02d}.{ext}"
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
            print(f"  ❌ Image generation failed for scene {scene_id}: {e}")
            raise

    def generate_batch(self, scenes: list, output_dir: str) -> list:
        """
        Generate images for all scenes in a script.
        Returns list of (scene_id, image_path) tuples.
        """
        results = []
        total = len(scenes)

        print(f"\n🖼️  Generating {total} images...")
        print(f"   Model: {self.model}")
        print(f"   Resolution: {self.resolution}\n")

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id", i + 1)
            prompt = scene.get("image_prompt", "")

            if not prompt:
                print(f"  ⏭️  Scene {scene_id}: No image prompt, skipping")
                continue

            try:
                image_path = self.generate(
                    prompt=prompt,
                    output_path=f"{output_dir}/images",
                    scene_id=scene_id,
                )
                results.append((scene_id, image_path))

                # Rate limiting — be gentle with the API
                if i < total - 1:
                    time.sleep(2)

            except Exception as e:
                print(f"  ❌ Scene {scene_id} failed: {e}")
                results.append((scene_id, None))

        successful = sum(1 for _, path in results if path is not None)
        print(f"\n📊 Image generation complete: {successful}/{total} successful")

        return results
