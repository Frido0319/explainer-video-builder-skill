#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文字幕 subs.srt（与 make_tts.py 同一份旁白文案）。
按每段音频实际时长把文案切分为字幕条：标点断句 → 每行≤22字 → 时长按字数比例分配。

用法：
  1. make_tts.py 先跑出 audio/{段名}.mp3
  2. 编辑下方 SEG_STARTS：各段配音起始秒（与 build_video.sh 的 adelay/1000 一致）
  3. python3 make_subs.py → 生成 subs.srt
  4. 合成时用 subtitles 滤镜烧录（见 references/ffmpeg-recipes.md）

字幕标点规范（用户要求，写死进脚本）：
  ① 行尾（尾巴）不加任何标点：。！？；，、：· 一律剥掉
  ② 字幕内不出现分号；：旁白里的 分号； 与 句末标点(。！？) 在句中一律拆成
     两条独立字幕，不再转写成分号；→ 拆开后各自行尾干净
  ③ 句中偶尔可保留逗号，、顿号、
  ④ 术语不断句：前向纠错、弱网场景 是整体，任何断行不得切在术语中间
"""
import re, subprocess, os
from make_tts import SEGS

# 行尾要剥掉的标点/空格（含全角空格）
TAIL_PUNCT = "。！？；，、：· "
# 硬断行符：句末标点与分号——出现即拆成两条独立字幕
HARD_BREAK = "。！？；"
# 软断行符：段内可优先在此断行，且标点保留在句中
SOFT_BREAK = "，、："
# 不可被断行切开的整体术语（可依项目扩充）
PROTECTED = ("前向纠错", "弱网场景")
MAX_LINE = 22  # 每行最大字数

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

def safe_cut(s):
    """在 ≤MAX_LINE 处找安全断点：不切断 PROTECTED 术语。返回断点下标。"""
    cut = MAX_LINE
    if len(s) <= cut:
        return len(s)
    for term in PROTECTED:
        pos = s.find(term)
        while pos != -1:
            if pos < cut < pos + len(term):
                cut = pos  # 断点切进术语内 → 回退到术语前
            pos = s.find(term, pos + 1)
    if cut == 0:
        cut = MAX_LINE
    return cut

def split_lines(text):
    """把旁白文案切成 ≤MAX_LINE 字的字幕行。
    硬断行：。！？； 处必断（句末/分号处拆成两条独立字幕，字幕内不出现这些符号）；
    软断行：单元内按 ，、： 优先断；整段超长时用 safe_cut 在术语外安全硬切。"""
    # 1) 硬断行 → 单元（每个单元不含 。！？；）
    units = []
    cur = ""
    for ch in text:
        cur += ch
        if ch in HARD_BREAK:
            units.append(cur)
            cur = ""
    if cur:
        units.append(cur)

    # 2) 单元内软断行 → 行
    lines = []
    for u in units:
        parts = re.findall(r"[^" + SOFT_BREAK + r"]+[" + SOFT_BREAK + r"]?", u)
        line = ""
        for p in parts:
            if len(line) + len(p) <= MAX_LINE:
                line += p
            else:
                if line:
                    lines.append(line)
                while len(p) > MAX_LINE:
                    cut = safe_cut(p)
                    lines.append(p[:cut])
                    p = p[cut:]
                line = p
        if line:
            lines.append(line)
    return lines or [text]

def clean_punct(line):
    """字幕行尾清理：剥掉行尾全部标点/空格（硬断行已保证行内无。！？；）"""
    return line.rstrip(TAIL_PUNCT)

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
        lines = [clean_punct(x) for x in split_lines(txt)]
        lines = [l for l in lines if l.strip()]
        # 硬约束：字幕行内不得再出现分号/句末标点
        bad = [l for l in lines if any(p in l for p in "；。！？")]
        if bad:
            raise SystemExit(f"字幕仍含分号/句末标点: {bad}")
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
