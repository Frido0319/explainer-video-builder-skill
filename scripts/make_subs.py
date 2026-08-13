#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文字幕 subs.srt（与 make_tts.py 同一份旁白文案）。
按每段音频实际时长把文案切分为字幕条：标点断句 → 每行≤22字 → 时长按字数比例分配。

用法：
  1. make_tts.py 先跑出 audio/{段名}.mp3
  2. 编辑下方 SEG_STARTS：各段配音起始秒（与 build_video.sh 的 adelay/1000 一致）
  3. python3 make_subs.py → 生成 subs.srt
  4. 合成时用 subtitles 滤镜烧录（见 references/ffmpeg-recipes.md）

字幕标点规范（用户要求）：
  ① 行尾（尾巴）不加任何标点：。！？；，、：· 一律剥掉
  ② 句中分隔用分号；：句中若出现句末标点(。！？) → 转成分号；
  ③ 句中偶尔可保留逗号，、顿号、
"""
import re, subprocess, os
from make_tts import SEGS

# 行尾要剥掉的标点/空格（含全角空格）
TAIL_PUNCT = "。！？；，、：· "
FULL_STOP = "。！？"

def clean_punct(line):
    """字幕标点清理：去尾标点 → 句中句末标点转分号（句中逗号/顿号保留）"""
    line = line.rstrip(TAIL_PUNCT)
    line = re.sub("[" + FULL_STOP + "]", "；", line)
    return line

# 各段配音的起始时间（秒），与 build_video.sh 时间轴（adelay 偏移毫秒/1000）一致
SEG_STARTS = {
    "seg0_title": 0.0,
    "seg1_bg": 5.6,
    "seg2_scheme": 24.4,
    "seg3_arch": 89.0,
    "seg4_feedback": 112.0,
    "seg5_demo": 124.5,
    # 若 SEGS 有更多段，按 build_video.sh 的实际偏移补上
}
MAX_LINE = 22  # 每行最大字数

def split_lines(text):
    """标点断句后贪心合并成 ≤MAX_LINE 字的行（标点随前文）"""
    parts = re.findall(r"[^，。；：、！？]+[，。；：、！？]?", text)
    lines, cur = [], ""
    for p in parts:
        if len(cur) + len(p) <= MAX_LINE:
            cur += p
        else:
            if cur:
                lines.append(cur)
            # 单段过长时按字数硬拆
            while len(p) > MAX_LINE:
                lines.append(p[:MAX_LINE])
                p = p[MAX_LINE:]
            cur = p
    if cur:
        lines.append(cur)
    return lines or [text]

def dur_of(name):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", f"audio/{name}.mp3"],
        capture_output=True, text=True).stdout.strip()
    return float(out)

def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def main():
    cues = []
    idx = 1
    for name, txt in SEGS:
        if name not in SEG_STARTS:
            continue
        start = SEG_STARTS[name]
        dur = dur_of(name)
        end = start + dur
        lines = [l for l in (clean_punct(x) for x in split_lines(txt)) if l.strip()]
        total = sum(len(l) for l in lines)
        pos = start
        for i, line in enumerate(lines):
            if i == len(lines) - 1:
                a, b = pos, end
            else:
                d = (end - start) * len(line) / total
                a, b = pos, min(pos + d, end)
                pos += d
            if b - a < 0.05:
                continue
            cues.append(f"{idx}\n{srt_time(a)} --> {srt_time(b)}\n{line}\n")
            idx += 1
    with open("subs.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(cues))
    print(f"subs.srt 生成 {idx-1} 条字幕")

if __name__ == "__main__":
    main()
