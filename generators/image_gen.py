"""
ClipFactory — Image Generator Module
Generates images from text prompts using Nano Banana 2 (Gemini API).
Supports dual-frame generation for Kling O3 (start + end frame).
Supports reference images (product photos) for visual accuracy.
Uses start frame as reference when generating end frame for consistency.
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

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  Pillow not installed. Run: pip install Pillow")


class ImageGenerator:
    """Generate images via Gemini API (Nano Banana 2) with reference image support."""

    def __init__(self, config: dict, project_root: str = None):
        self.config = config.get("image_generation", {})
        self.model = self.config.get("model", "gemini-2.0-flash-exp")
        self.resolution = self.config.get("resolution", "1024x1024")
        self.project_root = project_root or os.path.dirname(os.path.dirname(__file__))

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        if HAS_GENAI:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None

    def _load_reference_images(self, reference_str: str) -> list:
        """
        Load reference image(s) from a reference_image path string.
        Supports multiple images separated by ' + '.
        Returns list of PIL Image objects.
        """
        if not reference_str or not HAS_PIL:
            return []

        images = []
        paths = [p.strip() for p in reference_str.split("+")]

        for path in paths:
            # Resolve relative to project root
            if not os.path.isabs(path):
                full_path = os.path.join(self.project_root, path)
            else:
                full_path = path

            if os.path.exists(full_path):
                try:
                    img = PILImage.open(full_path)
                    images.append(img)
                    print(f"     📎 Reference: {os.path.basename(full_path)}")
                except Exception as e:
                    print(f"     ⚠️  Could not load reference: {full_path}: {e}")
            else:
                print(f"     ⚠️  Reference not found: {full_path}")

        return images

    def _load_image_as_pil(self, image_path: str):
        """Load a generated image as PIL Image for use as reference."""
        if not HAS_PIL or not image_path:
            return None
        try:
            return PILImage.open(image_path)
        except Exception as e:
            print(f"     ⚠️  Could not load image as reference: {e}")
            return None

    def generate(self, prompt: str, output_path: str, scene_id: int = 0,
                 suffix: str = "", reference_images: list = None) -> str:
        """
        Generate a single image from a text prompt, optionally with reference images.

        Args:
            prompt: Text prompt for image generation
            output_path: Directory to save the image
            scene_id: Scene number for naming
            suffix: Optional suffix for filename (e.g., '_start', '_end')
            reference_images: Optional list of PIL Image objects to use as references
        """
        if not self.client:
            raise RuntimeError("google-genai library not available")

        label = f"scene {scene_id}"
        if suffix:
            label += f" ({suffix.strip('_')} frame)"

        ref_count = len(reference_images) if reference_images else 0
        ref_label = f" + {ref_count} reference(s)" if ref_count else ""
        print(f"  🎨 Generating image for {label}{ref_label}...")
        print(f"     Prompt: {prompt[:80]}...")

        try:
            # Build content parts: reference images first, then text prompt
            content_parts = []

            if reference_images:
                for ref_img in reference_images:
                    content_parts.append(ref_img)

            content_parts.append(prompt)

            response = self.client.models.generate_content(
                model=self.model,
                contents=content_parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                    temperature=1.0,
                ),
            )

            # Extract image from response
            image_saved = False
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
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
                for part in response.candidates[0].content.parts:
                    if part.text:
                        print(f"  ⚠️  Model returned text instead of image: {part.text[:200]}")
                raise RuntimeError("No image generated — model did not return image data")

        except Exception as e:
            print(f"  ❌ Image generation failed for {label}: {e}")
            raise

    def generate_pair(self, start_prompt: str, end_prompt: str,
                      output_dir: str, scene_id: int = 0,
                      reference_image_str: str = None) -> tuple:
        """
        Generate a start + end frame pair for Kling O3 dual-frame animation.

        Strategy:
        1. Start frame: Generated with product reference photos as context
        2. End frame: Generated with product photos + start frame as context
           → This ensures the same person/scene/products in both frames

        Returns (start_image_path, end_image_path).
        """
        output_path = f"{output_dir}/images"

        print(f"\n  🖼️  Generating frame pair for scene {scene_id}...")

        # Load product reference images
        ref_images = self._load_reference_images(reference_image_str)

        # === PASS 1: Generate start frame with product references ===
        start_path = self.generate(
            prompt=start_prompt,
            output_path=output_path,
            scene_id=scene_id,
            suffix="_start",
            reference_images=ref_images if ref_images else None,
        )

        # Rate limiting
        time.sleep(2)

        # === PASS 2: Generate end frame with product refs + start frame ===
        # Use the start frame as additional reference for visual consistency
        end_refs = list(ref_images) if ref_images else []
        start_frame_pil = self._load_image_as_pil(start_path)
        if start_frame_pil:
            end_refs.append(start_frame_pil)
            print(f"     🔗 Using start frame as reference for end frame consistency")

        # Enhance end prompt with consistency instruction
        consistency_prefix = (
            "Using the provided reference image(s) as visual context — "
            "maintain the EXACT same person, scene, products, lighting, and style. "
            "Only change what is described in the prompt: "
        )
        enhanced_end_prompt = consistency_prefix + end_prompt

        end_path = self.generate(
            prompt=enhanced_end_prompt,
            output_path=output_path,
            scene_id=scene_id,
            suffix="_end",
            reference_images=end_refs if end_refs else None,
        )

        return start_path, end_path

    def generate_batch(self, scenes: list, output_dir: str,
                       scene_key: str = "scenes") -> list:
        """
        Generate images for all scenes in a script.
        Supports both single-frame (legacy) and dual-frame (O3) formats.
        Automatically uses reference images when specified in scene data.

        Returns list of (scene_id, start_path, end_path) tuples.
        end_path is None for single-frame scenes.
        """
        results = []
        total = len(scenes)

        has_dual = any(s.get("start_image_prompt") for s in scenes)
        has_refs = any(s.get("reference_image") for s in scenes)

        mode = "dual-frame (O3)" if has_dual else "single-frame (legacy)"
        ref_mode = " + product references" if has_refs else ""
        print(f"\n🖼️  Generating {total} {'frame pairs' if has_dual else 'images'}...")
        print(f"   Model: {self.model}")
        print(f"   Mode:  {mode}{ref_mode}")
        print(f"   Resolution: {self.resolution}\n")

        for i, scene in enumerate(scenes):
            scene_id = scene.get("scene_id") or scene.get("clip_id", i + 1)

            start_prompt = scene.get("start_image_prompt") or scene.get("image_prompt", "")
            end_prompt = scene.get("end_image_prompt")
            reference_image_str = scene.get("reference_image")

            if not start_prompt:
                print(f"  ⏭️  Scene {scene_id}: No image prompt, skipping")
                results.append((scene_id, None, None))
                continue

            try:
                if end_prompt:
                    # Dual-frame mode (O3) — with reference images and consistency
                    start_path, end_path = self.generate_pair(
                        start_prompt=start_prompt,
                        end_prompt=end_prompt,
                        output_dir=output_dir,
                        scene_id=scene_id,
                        reference_image_str=reference_image_str,
                    )
                    results.append((scene_id, start_path, end_path))
                else:
                    # Single-frame mode (legacy / backward compatible)
                    ref_images = self._load_reference_images(reference_image_str)
                    image_path = self.generate(
                        prompt=start_prompt,
                        output_path=f"{output_dir}/images",
                        scene_id=scene_id,
                        reference_images=ref_images if ref_images else None,
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
