#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""edge-tts 中文配音生成。逐段合成，输出到 audio/，并打印每段时长（供时间轴）。
依赖：pip install edge-tts==7.2.8；ffprobe（ffmpeg 自带）。

用法：
  1. 编辑下方 NARRATION 列表（每段一句/一段话）
  2. python3 make_tts.py
  3. 输出 audio/seg{N}.mp3 + 控制台打印每段时长秒数，据此排画面段边界
"""
import os
import subprocess
import sys

VOICE = "zh-CN-YunxiNeural"   # 男声；备选 zh-CN-XiaoxiaoNeural 女声
RATE = "+0%"                  # 语速：+8% 略快
OUT_DIR = "audio"

# ================= 配音文案（叙事定稿后填） =================
NARRATION = [
    "这里是片头主标题，一句话介绍项目。",                    # seg0 片头
    "这是背景段，讲应用场景和为什么要做这件事。",              # seg1 背景+痛点
    "这是方案段，讲核心技术原理，如何解决问题。",              # seg2 方案
    "这是架构段，讲系统架构和数据流走向。",                    # seg3 架构
    "这是反馈闭环段，讲机制如何闭环。",                        # seg4 反馈
    "下面展示实测效果。机载端回传的视频经编码和公网传输，地面站解码播放稳定流畅。",  # seg5 实测
    # 结束页如需配音可加
]
# ==========================================================


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for i, text in enumerate(NARRATION):
        out = os.path.join(OUT_DIR, f"seg{i}.mp3")
        cmd = ["edge-tts", "--voice", VOICE, "--rate", RATE,
               "--text", text, "--write-media", out]
        print(f"[{i}] 生成 {out} …")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print("  edge-tts 失败:", r.stderr or r.stdout)
            sys.exit(1)
        # 读时长
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=nw=1:nk=1", out],
            capture_output=True, text=True)
        try:
            d = round(float(dur.stdout.strip()), 2)
        except ValueError:
            d = 0.0
        print(f"  seg{i} 时长 {d}s")

    print("\n配音生成完毕。把每段时长累加成画面段边界（秒），"
          "再按累积毫秒偏移写进 build_video.sh 的 adelay。")


if __name__ == "__main__":
    main()
