#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检测真实演示视频的黑屏起点（用于决定实测段该截到哪）。
原理：每隔 step 秒抽一帧，测画面上半部的平均亮度。
黑屏特征：上部亮度骤降（如 75 → ~0）。返回最后一个干净时间点。

用法：python3 check_blackscreen.py <视频.mp4> [step=1.0]
输出：每帧 时间(秒) 上部平均亮度；末尾给出黑屏起点建议。
"""
import subprocess
import sys
import tempfile
import os

from PIL import Image


def probe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def frame_brightness(video, t, tmpdir):
    """抽 t 秒处一帧，返回 (上半部平均亮度, 全帧平均亮度)。"""
    png = os.path.join(tmpdir, f"f_{t:06.1f}.png")
    subprocess.run(
        ["ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", video,
         "-frames:v", "1", "-q:v", "2", png],
        capture_output=True)
    if not os.path.exists(png):
        return None
    im = Image.open(png).convert("L")
    w, h = im.size
    top = im.crop((0, 0, w, int(h * 0.35)))
    top_stats = list(top.getextrema())
    full_stats = list(im.getextrema())
    os.remove(png)
    return (sum(top_stats) / 2, sum(full_stats) / 2)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    video = sys.argv[1]
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0

    dur = probe_duration(video)
    print(f"视频时长 {dur:.2f}s，步长 {step}s")
    tmpdir = tempfile.mkdtemp(prefix="bs_")
    prev_top = None
    first_drop = None
    t = 0.0
    while t < dur:
        r = frame_brightness(video, t, tmpdir)
        if r is None:
            print(f"{t:7.2f}s  抽帧失败")
        else:
            top, full = r
            flag = ""
            if prev_top is not None and prev_top - top > 40:
                flag = "  <-- 上部亮度骤降（黑屏起点候选）"
                if first_drop is None:
                    first_drop = t
            print(f"{t:7.2f}s  上部平均亮度 {top:6.1f}  全帧 {full:6.1f}{flag}")
            prev_top = top
        t += step

    if first_drop is not None:
        print(f"\n结论：黑屏起点 ≈ {first_drop:.2f}s。"
              f"实测段时长建议取 {max(0.5, first_drop - 0.7):.1f}s（留余量）。")
    else:
        print("\n结论：未检测到上部亮度骤降，可安全使用全片。")


if __name__ == "__main__":
    main()
