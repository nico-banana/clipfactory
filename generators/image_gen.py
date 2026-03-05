"""
ClipFactory — Image Generator Module
Generates images via fal.ai Nano Banana Pro (Gemini 3 Pro Image).
Supports reference images (product photos) for visual accuracy.
Uses fal_client for unified billing through fal.ai.
"""

import os
import time
from pathlib import Path

try:
    import fal_client
    HAS_FAL = True
except ImportError:
    HAS_FAL = False
    print("⚠️  fal-client not installed. Run: pip install fal-client")

try:
    import requests as req_lib
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class ImageGenerator:
    """Generate images via fal.ai Nano Banana Pro with reference image support."""

    def __init__(self, config: dict, project_root: str = None):
        self.config = config.get("image_generation", {})
        self.model = self.config.get("model", "nano-banana-pro-preview")
        self.resolution = self.config.get("resolution", "4K")
        self.aspect_ratio = self.config.get("aspect_ratio", "9:16")
        self.project_root = project_root or os.path.dirname(os.path.dirname(__file__))

        # Map model name to fal.ai endpoint
        model_map = {
            "nano-banana-pro-preview": "fal-ai/nano-banana-pro-preview",
            "nano-banana-pro": "fal-ai/nano-banana-pro",
            "recraft-v3": "fal-ai/recraft/v3/text-to-image",
            "flux-pro-ultra": "fal-ai/flux-pro/v1.1-ultra",
        }
        self.fal_model = model_map.get(self.model, self.model)

        # Normalize resolution
        res_map = {"1080x1920": "1K", "1920x1080": "1K", "1024x1024": "1K",
                   "2160x3840": "2K", "3840x2160": "2K",
                   "1K": "1K", "2K": "2K", "4K": "4K"}
        self.image_size = res_map.get(self.resolution,
                                      self.resolution.upper() if self.resolution.upper() in ["1K", "2K", "4K"] else "1K")

        if not HAS_FAL:
            raise RuntimeError("fal-client not installed")

        if not os.environ.get("FAL_KEY"):
            raise ValueError("FAL_KEY environment variable not set")

    def _upload_reference(self, path: str) -> str:
        """Upload a local image file to fal.ai CDN and return the URL."""
        if not os.path.isabs(path):
            full_path = os.path.join(self.project_root, path)
        else:
            full_path = path

        if not os.path.exists(full_path):
            print(f"     ⚠️  Reference not found: {full_path}")
            return None

        try:
            url = fal_client.upload_file(full_path)
            print(f"     📎 Reference: {os.path.basename(full_path)}")
            return url
        except Exception as e:
            print(f"     ⚠️  Upload failed for {os.path.basename(full_path)}: {e}")
            return None

    def _load_reference_urls(self, reference_str: str) -> list:
        """
        Upload reference image(s) from a reference_image path string.
        Supports multiple images separated by ' + '.
        Returns list of fal.ai CDN URLs.
        """
        if not reference_str:
            return []

        urls = []
        paths = [p.strip() for p in reference_str.split("+")]

        for path in paths:
            url = self._upload_reference(path)
            if url:
                urls.append(url)

        return urls

    def generate(self, prompt: str, output_path: str, scene_id: int = 0,
                 suffix: str = "", reference_urls: list = None) -> str:
        """
        Generate a single image from a text prompt, optionally with reference images.

        Args:
            prompt: Text prompt for image generation
            output_path: Directory to save the image
            scene_id: Scene number for naming
            suffix: Optional suffix for filename
            reference_urls: Optional list of fal.ai CDN URLs for reference images
        """
        label = f"scene {scene_id}"
        if suffix:
            label += f" ({suffix.strip('_')} frame)"

        ref_count = len(reference_urls) if reference_urls else 0
        ref_label = f" + {ref_count} reference(s)" if ref_count else ""
        print(f"  🎨 Generating image for {label}{ref_label}...")
        print(f"     Prompt: {prompt[:80]}...")

        try:
            arguments = {
                "prompt": prompt,
                "aspect_ratio": self.aspect_ratio,
                "resolution": self.image_size,
                "num_images": 1,
            }

            # Add reference images if provided
            if reference_urls:
                arguments["image_urls"] = reference_urls

            result = fal_client.subscribe(
                self.fal_model,
                arguments=arguments,
            )

            # Extract image URL from result
            image_url = None
            if isinstance(result, dict):
                images = result.get("images", [])
                if images and isinstance(images[0], dict):
                    image_url = images[0].get("url")
                elif result.get("image", {}).get("url"):
                    image_url = result["image"]["url"]

            if not image_url:
                raise RuntimeError(f"No image URL in response: {result}")

            # Download and save image
            Path(output_path).mkdir(parents=True, exist_ok=True)
            file_path = f"{output_path}/scene_{scene_id:02d}{suffix}.jpg"

            response = req_lib.get(image_url, stream=True)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"  ✅ Image saved: {file_path}")
            return file_path

        except Exception as e:
            print(f"  ❌ Image generation failed for {label}: {e}")
            raise

    def generate_pair(self, start_prompt: str, end_prompt: str,
                      output_dir: str, scene_id: int = 0,
                      reference_image_str: str = None) -> tuple:
        """
        Generate a start + end frame pair for dual-frame animation.
        Returns (start_image_path, end_image_path).
        """
        output_path = f"{output_dir}/images"

        print(f"\n  🖼️  Generating frame pair for scene {scene_id}...")

        # Upload product reference images
        ref_urls = self._load_reference_urls(reference_image_str)

        # === PASS 1: Generate start frame ===
        start_path = self.generate(
            prompt=start_prompt,
            output_path=output_path,
            scene_id=scene_id,
            suffix="_start",
            reference_urls=ref_urls if ref_urls else None,
        )

        time.sleep(2)

        # === PASS 2: Generate end frame with start frame as reference ===
        end_refs = list(ref_urls) if ref_urls else []
        # Upload start frame as reference for consistency
        start_url = self._upload_reference(start_path)
        if start_url:
            end_refs.append(start_url)
            print(f"     🔗 Using start frame as reference for end frame consistency")

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
            reference_urls=end_refs if end_refs else None,
        )

        return start_path, end_path

    def generate_batch(self, scenes: list, output_dir: str,
                       scene_key: str = "scenes") -> list:
        """
        Generate images for all scenes in a script.
        Supports both single-frame and dual-frame formats.

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
        print(f"   Model: {self.fal_model}")
        print(f"   Mode:  {mode}{ref_mode}")
        print(f"   Resolution: {self.image_size}\n")

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
                    # Dual-frame mode
                    start_path, end_path = self.generate_pair(
                        start_prompt=start_prompt,
                        end_prompt=end_prompt,
                        output_dir=output_dir,
                        scene_id=scene_id,
                        reference_image_str=reference_image_str,
                    )
                    results.append((scene_id, start_path, end_path))
                else:
                    # Single-frame mode
                    ref_urls = self._load_reference_urls(reference_image_str)
                    image_path = self.generate(
                        prompt=start_prompt,
                        output_path=f"{output_dir}/images",
                        scene_id=scene_id,
                        reference_urls=ref_urls if ref_urls else None,
                    )
                    results.append((scene_id, image_path, None))

                # Rate limiting
                if i < total - 1:
                    time.sleep(2)

            except Exception as e:
                print(f"  ❌ Scene {scene_id} failed: {e}")
                results.append((scene_id, None, None))

        successful = sum(1 for _, sp, _ in results if sp is not None)
        print(f"\n📊 Image generation complete: {successful}/{total} successful")

        return results
