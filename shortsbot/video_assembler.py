import os
import subprocess


def _escape_drawtext(text: str) -> str:
    """ffmpeg drawtext 필터용 특수문자 이스케이프."""
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _build_segment(image_path: str | None, audio_path: str, text: str, out_path: str) -> None:
    drawtext = (
        f"drawtext=text='{_escape_drawtext(text)}':fontcolor=white:fontsize=48:"
        "box=1:boxcolor=black@0.6:boxborderw=16:x=(w-text_w)/2:y=h-200"
    )
    if image_path is None:
        video_input = ["-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1080x1920"]
    else:
        video_input = ["-loop", "1", "-i", image_path]

    cmd = [
        "ffmpeg", "-y",
        *video_input,
        "-i", audio_path,
        "-vf",
        f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{drawtext}",
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
        "-pix_fmt", "yuv420p", "-shortest",
        out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def assemble_video(
    sentences: list[str],
    audio_paths: list[str],
    image_paths: list[str | None],
    out_path: str,
) -> str:
    """문장별 세그먼트(이미지/단색배경 + 오디오 + 자막)를 만들어 이어 붙인다."""
    if not (len(sentences) == len(audio_paths) == len(image_paths)):
        raise ValueError(
            "문장/오디오/이미지 개수가 일치하지 않음: "
            f"{len(sentences)}/{len(audio_paths)}/{len(image_paths)}"
        )

    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    segment_paths = []
    for i, (sentence, audio_path, image_path) in enumerate(
        zip(sentences, audio_paths, image_paths), start=1
    ):
        segment_path = os.path.join(out_dir, f"segment_{i}.mp4")
        _build_segment(image_path, audio_path, sentence, segment_path)
        segment_paths.append(segment_path)

    concat_list_path = os.path.join(out_dir, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for segment_path in segment_paths:
            f.write(f"file '{os.path.abspath(segment_path)}'\n")

    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c", "copy", out_path,
        ],
        check=True,
        capture_output=True,
    )
    return out_path
