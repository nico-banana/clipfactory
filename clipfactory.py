#!/usr/bin/env python3
"""
ClipFactory — Automated Ad Clip Generation Pipeline
====================================================

Generate images from scripts and animate them into ad clips at scale.
Supports Kling O3 dual-frame animation for smooth transitions.

Usage:
    python clipfactory.py scripts/banaani-ugc-01.json
    python clipfactory.py scripts/banaani-ugc-01.json --images-only
    python clipfactory.py scripts/banaani-ugc-01.json --animate-only
    python clipfactory.py scripts/banaani-ugc-01.json --scene 1

Environment variables required:
    GEMINI_API_KEY  - Google AI Studio API key
    FAL_KEY         - fal.ai API key
"""

import argparse
import json
import os
import sys
import time
import yaml
from pathlib import Path
from datetime import datetime


def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file."""
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_script(script_path: str) -> dict:
    """Load a script JSON file."""
    with open(script_path, "r") as f:
        return json.load(f)


def get_scenes(script: dict, scene_filter: int = None) -> list:
    """
    Extract scenes from script, supporting both formats:
    - Legacy: script["scenes"] with image_prompt
    - New: script["broll_clips"] with start_image_prompt / end_image_prompt
    """
    # Prefer broll_clips (new format), fall back to scenes (legacy)
    scenes = script.get("broll_clips") or script.get("scenes", [])

    if scene_filter is not None:
        filter_key = "clip_id" if "broll_clips" in script else "scene_id"
        scenes = [s for s in scenes if s.get(filter_key) == scene_filter
                  or s.get("scene_id") == scene_filter
                  or s.get("clip_id") == scene_filter]
        if not scenes:
            print(f"❌ Scene/clip {scene_filter} not found in script")

    return scenes


def run_pipeline(script_path: str, config_path: str = None,
                 images_only: bool = False, animate_only: bool = False,
                 scene_filter: int = None, skip_assembly: bool = False):
    """
    Run the full ClipFactory pipeline.

    Args:
        script_path: Path to the script JSON file
        config_path: Optional path to config YAML
        images_only: Only generate images, skip animation
        animate_only: Only animate existing images, skip generation
        scene_filter: Only process this specific scene number
        skip_assembly: Skip the final assembly step
    """
    # Load config and script
    config = load_config(config_path)
    script = load_script(script_path)

    project_name = script.get("project", "untitled")
    client = script.get("client", "unknown")
    scenes = get_scenes(script, scene_filter)

    if not scenes:
        return

    # Detect format
    has_broll = "broll_clips" in script
    has_dual_frame = any(s.get("start_image_prompt") for s in scenes)

    # Set up output directory
    output_base = config.get("output", {}).get("base_dir", "output")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(
        os.path.dirname(__file__),
        output_base,
        client,
        f"{project_name}_{timestamp}"
    )
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save script copy to output for reference
    with open(f"{output_dir}/script.json", "w") as f:
        json.dump(script, f, indent=2, ensure_ascii=False)

    print("=" * 60)
    print(f"🏭 ClipFactory Pipeline")
    print(f"=" * 60)
    print(f"   Project:  {project_name}")
    print(f"   Client:   {client}")
    print(f"   Scenes:   {len(scenes)}")
    print(f"   Format:   {'Dual-frame (O3)' if has_dual_frame else 'Single-frame (legacy)'}")
    print(f"   Output:   {output_dir}")
    print(f"   Mode:     {'Images only' if images_only else 'Animate only' if animate_only else 'Full pipeline'}")
    print(f"=" * 60)

    start_time = time.time()
    image_results = []  # List of (scene_id, start_path, end_path)
    clip_results = []

    # ─── STEP 1: Generate Images ───
    if not animate_only:
        from generators.image_gen import ImageGenerator

        try:
            project_root = os.path.dirname(os.path.abspath(__file__))
            img_gen = ImageGenerator(config, project_root=project_root)
            image_results = img_gen.generate_batch(scenes, output_dir)
        except ValueError as e:
            print(f"\n❌ Image generation setup failed: {e}")
            print("   Set FAL_KEY environment variable and try again.")
            return
        except Exception as e:
            print(f"\n❌ Image generation failed: {e}")
            return
    else:
        # Load existing images from output directory
        images_dir = f"{output_dir}/images"
        if not os.path.exists(images_dir) or not os.listdir(images_dir if os.path.exists(images_dir) else "."):
            # Try to find the most recent output for this project that HAS images
            client_dir = os.path.join(os.path.dirname(__file__), output_base, client)
            if os.path.exists(client_dir):
                dirs = sorted([d for d in os.listdir(client_dir) if project_name in d])
                # Walk backwards to find most recent dir with actual images
                for candidate in reversed(dirs):
                    candidate_images = os.path.join(client_dir, candidate, "images")
                    if os.path.exists(candidate_images) and any(
                        f.startswith("scene_") for f in os.listdir(candidate_images)
                    ):
                        images_dir = candidate_images
                        output_dir = os.path.join(client_dir, candidate)
                        print(f"  📂 Using existing images from: {images_dir}")
                        break

        if os.path.exists(images_dir):
            # Discover images — support both single and dual-frame naming
            files = sorted(os.listdir(images_dir))
            discovered = {}

            for f in files:
                if not f.startswith("scene_") or f.endswith(".txt"):
                    continue

                name = f.rsplit(".", 1)[0]  # Remove extension
                if "_start" in name:
                    scene_id = int(name.split("_")[1])
                    discovered.setdefault(scene_id, [None, None])
                    discovered[scene_id][0] = os.path.join(images_dir, f)
                elif "_end" in name:
                    scene_id = int(name.split("_")[1])
                    discovered.setdefault(scene_id, [None, None])
                    discovered[scene_id][1] = os.path.join(images_dir, f)
                else:
                    # Legacy single-frame naming
                    scene_id = int(name.split("_")[1])
                    discovered.setdefault(scene_id, [None, None])
                    discovered[scene_id][0] = os.path.join(images_dir, f)

            for sid in sorted(discovered.keys()):
                start, end = discovered[sid]
                image_results.append((sid, start, end))

            dual = sum(1 for _, _, e in image_results if e)
            print(f"  📂 Found {len(image_results)} scenes ({dual} dual-frame, {len(image_results)-dual} single-frame)")
        else:
            print(f"  ❌ No images found. Run without --animate-only first.")
            return

    if images_only:
        elapsed = time.time() - start_time
        successful = sum(1 for _, sp, _ in image_results if sp)
        print(f"\n{'=' * 60}")
        print(f"✅ Images generated in {elapsed:.1f}s")
        print(f"   {successful}/{len(scenes)} scenes successful")
        print(f"   Output: {output_dir}/images/")
        print(f"{'=' * 60}")
        return

    # ─── STEP 2: Animate Images ───
    from generators.animation import AnimationEngine

    try:
        animator = AnimationEngine(config)
        clip_results = animator.animate_batch(scenes, image_results, output_dir)
    except ValueError as e:
        print(f"\n❌ Animation setup failed: {e}")
        print("   Set FAL_KEY environment variable and try again.")
        return
    except Exception as e:
        print(f"\n❌ Animation failed: {e}")
        return

    # ─── STEP 3: Add Text Overlays ───
    from assembler import ClipAssembler

    assembler = ClipAssembler(config)

    # Apply text overlays where specified
    for scene in scenes:
        scene_id = scene.get("scene_id") or scene.get("clip_id")
        text = scene.get("text_overlay")

        if not text:
            continue

        clip_path = next(
            (path for sid, path in clip_results if sid == scene_id and path),
            None
        )

        if clip_path:
            try:
                print(f"  📝 Adding text overlay to scene {scene_id}: \"{text}\"")
                overlay_path = assembler.add_text_overlay(clip_path, text)
                # Replace clip path with overlaid version
                clip_results = [
                    (sid, overlay_path if sid == scene_id else path)
                    for sid, path in clip_results
                ]
            except Exception as e:
                print(f"  ⚠️  Text overlay failed for scene {scene_id}: {e}")

    # ─── STEP 4: Assemble Final Video ───
    if not skip_assembly and len(clip_results) > 1:
        try:
            final_path = assembler.assemble(
                clip_results, output_dir, project_name
            )
        except Exception as e:
            print(f"\n❌ Assembly failed: {e}")
            final_path = None
    else:
        final_path = None

    # ─── Summary ───
    elapsed = time.time() - start_time
    successful_images = sum(1 for _, sp, _ in image_results if sp)
    successful_clips = sum(1 for _, p in clip_results if p)

    print(f"\n{'=' * 60}")
    print(f"🏁 Pipeline Complete!")
    print(f"{'=' * 60}")
    print(f"   Images:    {successful_images}/{len(scenes)} generated")
    print(f"   Clips:     {successful_clips}/{len(scenes)} animated")
    if final_path:
        print(f"   Final:     {final_path}")
    print(f"   Time:      {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"   Output:    {output_dir}/")
    print(f"{'=' * 60}")

    # Save run report
    report = {
        "project": project_name,
        "client": client,
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "scenes_total": len(scenes),
        "images_generated": successful_images,
        "clips_animated": successful_clips,
        "final_video": final_path,
        "config": config,
    }

    with open(f"{output_dir}/report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description="ClipFactory — Automated Ad Clip Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clipfactory.py scripts/banaani-ugc-01.json
  python clipfactory.py scripts/banaani-ugc-01.json --images-only
  python clipfactory.py scripts/banaani-ugc-01.json --animate-only
  python clipfactory.py scripts/banaani-ugc-01.json --scene 1
        """
    )

    parser.add_argument("script", help="Path to script JSON file")
    parser.add_argument("--config", help="Path to config YAML (default: config.yaml)")
    parser.add_argument("--images-only", action="store_true",
                        help="Only generate images, skip animation")
    parser.add_argument("--animate-only", action="store_true",
                        help="Only animate existing images")
    parser.add_argument("--scene", type=int, default=None,
                        help="Process only this scene number")
    parser.add_argument("--skip-assembly", action="store_true",
                        help="Skip final video assembly")

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"❌ Script not found: {args.script}")
        sys.exit(1)

    run_pipeline(
        script_path=args.script,
        config_path=args.config,
        images_only=args.images_only,
        animate_only=args.animate_only,
        scene_filter=args.scene,
        skip_assembly=args.skip_assembly,
    )


if __name__ == "__main__":
    main()
