#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成品视频无视觉自检：ffprobe 基础信息 + 抽查帧亮度 + 可选 OCR +
卡片比对 + 字幕带检查。
用法：
  python3 verify_video.py <成品.mp4> [t1,t2,...]          # 抽查时间点（秒）
  python3 verify_video.py <成品.mp4> --all=2               # 每 2 秒抽一帧全查
  python3 verify_video.py <成品.mp4> --cards=cards         # 逐段抽帧与 cards/*.png 比对 + 字幕带检查
输出：时长/分辨率/编码；每帧亮度区间 + 上部亮度（黑屏检测）；OCR（若 tesseract 可用）；
      --cards 模式：卡片区 diff（应<4）+ 字幕带(y945-1080)渲染像素（有配音段应>300）。
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

SUB_BAND_TOP = 945       # 字幕带起始：卡片内容必须 ≤940，以下留给字幕
SUB_BAND_MIN_PX = 300    # 字幕带最低渲染像素（有配音段应远超）


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


def check_card(video, t, tmpdir, cards_dir):
    """逐段抽帧，与 cards/*.png 比对：卡片区(y<945) diff<4 且字幕带确有字幕。
    抽样时间 t 必须是"该卡片所在段内、且该段配音正在播"的中间点。"""
    png = os.path.join(tmpdir, f"c_{t:06.1f}.png")
    run("ffmpeg", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", png)
    if not os.path.exists(png):
        print(f"[{t:7.2f}s] 抽帧失败"); return
    v = np.array(Image.open(png).convert("RGB"), dtype=np.int16)
    # 找最接近的卡片：逐张比卡片区，取 diff 最小者
    best, best_diff, best_card = None, 1e9, None
    for name in sorted(os.listdir(cards_dir)):
        if not name.endswith(".png") or name.startswith("demo"):
            continue
        s = np.array(Image.open(os.path.join(cards_dir, name)).convert("RGB"),
                     dtype=np.int16)
        diff = float(np.abs(v[:SUB_BAND_TOP] - s[:SUB_BAND_TOP]).mean())
        if diff < best_diff:
            best, best_diff, best_card = s, diff, name
    card_ok = best_diff < 4
    # 字幕带：白卡源在 y945-1080 无内容，帧里此处暗像素=字幕
    if best is not None:
        band_diff = np.abs(v[SUB_BAND_TOP:1080] - best[SUB_BAND_TOP:1080]).max(axis=2)
        sub_px = int((band_diff > 40).sum())
    else:
        sub_px = 0
    sub_ok = sub_px > SUB_BAND_MIN_PX
    print(f"[{t:7.2f}s] 匹配卡片={best_card} 卡区diff={best_diff:5.1f} "
          f"{'✓' if card_ok else '✗'} 字幕带渲染px={sub_px:6d} "
          f"{'✓' if sub_ok else '✗(此段无配音则忽略)'}")
    os.remove(png)
    return card_ok


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    video = sys.argv[1]
    tmpdir = tempfile.mkdtemp(prefix="vf_")
    probe(video)

    cards_mode = None
    for a in sys.argv[2:]:
        if a.startswith("--cards"):
            cards_mode = a.split("=", 1)[1] if "=" in a else "cards"

    do_ocr = run("which", "tesseract").returncode == 0

    if cards_mode:
        print(f"== 卡片比对模式（cards_dir={cards_mode}，OCR={'开' if do_ocr else '关'}）==")
        # 段内抽样：传入的每个时间点对应一段卡片中点
        times = [float(x) for x in sys.argv[3:] if x and not x.startswith("--")]
        if not times:
            times = [3.0, 12.0, 18.0, 33.0, 99.0, 117.0]  # 默认按九段结构取
        for t in times:
            check_card(video, t, tmpdir, cards_mode)
        return

    # 普通模式：解析抽查时间
    spec = None
    for a in sys.argv[2:]:
        if a.startswith("--all="):
            spec = a
        elif not a.startswith("--"):
            spec = a
    if spec is None:
        times = [2.0, 8.0, 20.0, 40.0, 65.0]
    elif spec.startswith("--all="):
        step = float(spec.split("=")[1])
        dur = float(run("ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "default=nw=1:nk=1",
                        video).stdout.strip())
        times = [round(i * step, 1) for i in range(int(dur / step) + 1)]
    else:
        times = [float(x) for x in spec.split(",")]

    print(f"== 抽查 {len(times)} 帧（OCR={'开' if do_ocr else '关（装 tesseract-ocr + tesseract-ocr-chi-sim 可开）'}）==")
    for t in times:
        check_frame(video, t, tmpdir, do_ocr=do_ocr)


if __name__ == "__main__":
    main()
