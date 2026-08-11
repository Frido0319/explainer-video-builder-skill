#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成品视频无视觉自检：ffprobe 基础信息 + 抽查帧亮度 + 可选 OCR。
用法：
  python3 verify_video.py <成品.mp4> [t1,t2,...]   # 抽查时间点（秒）
  python3 verify_video.py <成品.mp4> --all=2        # 每 2 秒抽一帧全查
输出：时长/分辨率/编码；每帧亮度区间 + 上部亮度（黑屏检测）；OCR 文本（若 tesseract 可用）。
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

try:
    import numpy as np
    HAVE_NP = True
except ImportError:
    HAVE_NP = False


def run(*args, **kw):
    return subprocess.run(list(args), capture_output=True, text=True, **kw)


def probe(video):
    d = run("ffprobe", "-v", "error", "-show_entries",
            "format=duration,size", "-of", "default=nw=1:nk=1", video)
    v = run("ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,codec_name,r_frame_rate",
            "-of", "default=nw=1:nk=1", video)
    a = run("ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,sample_rate",
            "-of", "default=nw=1:nk=1", video)
    print("== ffprobe ==")
    print("时长/大小:", d.stdout.replace("\n", "  "))
    print("视频流:", v.stdout.replace("\n", "  "))
    print("音频流:", a.stdout.replace("\n", "  "), "（缺音频=未接配音）")


def check_frame(video, t, tmpdir, do_ocr=False):
    png = os.path.join(tmpdir, f"f_{t:06.1f}.png")
    run("ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", video,
        "-frames:v", "1", "-q:v", "2", png)
    if not os.path.exists(png):
        print(f"[{t:7.2f}s] 抽帧失败")
        return
    im = Image.open(png).convert("L")
    w, h = im.size
    full = im.getextrema()
    top = im.crop((0, 0, w, int(h * 0.35))).getextrema()
    note = ""
    if full[0] < 20 and full[1] < 40:
        note = " !! 整帧近黑"
    elif top[0] < 20 and full[0] > 80:
        note = " !! 上部黑（顶部被黑屏污染）"
    if HAVE_NP:
        avg = float(np.asarray(im).mean())
        print(f"[{t:7.2f}s] 亮度范围 {full}  平均 {avg:6.1f}{note}")
    else:
        print(f"[{t:7.2f}s] 亮度范围 {full}{note}")
    if do_ocr:
        r = run("tesseract", png, "stdout", "-l", "chi_sim")
        txt = r.stdout.strip().replace("\n", " | ")
        print(f"    OCR: {txt[:160] if txt else '(空)'}")
    os.remove(png)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    video = sys.argv[1]
    tmpdir = tempfile.mkdtemp(prefix="vf_")
    probe(video)

    # 解析抽查时间
    if len(sys.argv) >= 3:
        spec = sys.argv[2]
        if spec.startswith("--all="):
            step = float(spec.split("=")[1])
            dur = float(run("ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "default=nw=1:nk=1",
                            video).stdout.strip())
            times = [round(x, 1) for x in
                     list(range(0, int(dur) + 1))] and [round(i * step, 1)
                     for i in range(int(dur / step) + 1)]
        else:
            times = [float(x) for x in spec.split(",")]
    else:
        times = [2.0, 8.0, 20.0, 40.0, 65.0]

    do_ocr = run("which", "tesseract").returncode == 0
    print(f"== 抽查 {len(times)} 帧（OCR={'开' if do_ocr else '关（装 tesseract-ocr + tesseract-ocr-chi-sim 可开）'}）==")
    for t in times:
        check_frame(video, t, tmpdir, do_ocr=do_ocr)


if __name__ == "__main__":
    main()
