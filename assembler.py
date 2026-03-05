"""
ClipFactory — Clip Assembler Module
Stitches animated clips into a final video using FFmpeg.
"""

import os
import subprocess
import tempfile
from pathlib import Path


class ClipAssembler:
    """Assemble individual clips into a final video using FFmpeg."""

    def __init__(self, config: dict):
        self.config = config.get("assembly", {})
        self.output_format = self.config.get("output_format", "mp4")
        self.codec = self.config.get("codec", "libx264")
        self.audio_codec = self.config.get("audio_codec", "aac")
        self.fps = self.config.get("fps", 30)

        # Check FFmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("⚠️  FFmpeg not found. Install it: brew install ffmpeg")

    def assemble(self, clip_results: list, output_dir: str,
                 project_name: str = "output") -> str:
        """
        Concatenate clips in scene order into a single video.

        Args:
            clip_results: List of (scene_id, clip_path) tuples
            output_dir: Directory to save the final video
            project_name: Name for the output file

        Returns:
            Path to the assembled video
        """
        # Filter out failed clips and sort by scene_id
        valid_clips = [
            (sid, path) for sid, path in clip_results
            if path is not None and os.path.exists(path)
        ]
        valid_clips.sort(key=lambda x: x[0])

        if not valid_clips:
            raise RuntimeError("No valid clips to assemble")

        print(f"\n🔗 Assembling {len(valid_clips)} clips...")

        # If only one clip, just copy it
        if len(valid_clips) == 1:
            output_path = f"{output_dir}/{project_name}.{self.output_format}"
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            subprocess.run([
                "cp", valid_clips[0][1], output_path
            ], check=True)
            print(f"  ✅ Single clip saved: {output_path}")
            return output_path

        # Create a concat file for FFmpeg
        concat_file = tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, prefix='clipfactory_'
        )

        try:
            for _, clip_path in valid_clips:
                abs_path = os.path.abspath(clip_path)
                concat_file.write(f"file '{abs_path}'\n")
            concat_file.close()

            output_path = f"{output_dir}/{project_name}.{self.output_format}"
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # First, normalize all clips to the same resolution and encoding
            normalized_clips = []
            for sid, clip_path in valid_clips:
                normalized_path = f"{output_dir}/_norm_scene_{sid:02d}.{self.output_format}"
                print(f"  📐 Normalizing scene {sid}...")

                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", clip_path,
                    "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,fps={self.fps}",
                    "-c:v", self.codec,
                    "-preset", "fast",
                    "-crf", "23",
                    "-an",  # Remove audio for now (we'll add voiceover separately)
                    "-pix_fmt", "yuv420p",
                    normalized_path
                ], capture_output=True, check=True)

                normalized_clips.append(normalized_path)

            # Write concat file with normalized clips
            with open(concat_file.name, 'w') as f:
                for norm_path in normalized_clips:
                    f.write(f"file '{os.path.abspath(norm_path)}'\n")

            # Concatenate
            print(f"  🔗 Concatenating {len(normalized_clips)} clips...")
            subprocess.run([
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file.name,
                "-c", "copy",
                output_path
            ], capture_output=True, check=True)

            # Clean up normalized intermediates
            for norm_path in normalized_clips:
                try:
                    os.remove(norm_path)
                except OSError:
                    pass

            # Get final video info
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries",
                 "format=duration", "-of", "csv=p=0", output_path],
                capture_output=True, text=True
            )
            duration = float(result.stdout.strip()) if result.stdout.strip() else 0

            print(f"  ✅ Final video saved: {output_path}")
            print(f"     Duration: {duration:.1f}s")

            return output_path

        finally:
            # Clean up temp concat file
            try:
                os.unlink(concat_file.name)
            except OSError:
                pass

    def add_text_overlay(self, video_path: str, text: str,
                         output_path: str = None) -> str:
        """Add text overlay to a video clip (for text_overlay scenes)."""
        if not output_path:
            base, ext = os.path.splitext(video_path)
            output_path = f"{base}_text{ext}"

        # Escape special characters for FFmpeg drawtext
        safe_text = text.replace("'", "\\'").replace(":", "\\:")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", (
                f"drawtext=text='{safe_text}'"
                f":fontsize=48:fontcolor=white"
                f":borderw=3:bordercolor=black"
                f":x=(w-text_w)/2:y=h-th-100"
                f":fontfile=/System/Library/Fonts/Helvetica.ttc"
            ),
            "-c:v", self.codec,
            "-c:a", "copy",
            output_path
        ], capture_output=True, check=True)

        return output_path
