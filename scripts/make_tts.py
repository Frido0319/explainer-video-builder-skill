#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""edge-tts 中文配音生成。逐段合成，输出到 audio/（seg0_title.mp3 …）。
依赖：pip install edge-tts==7.2.8；ffprobe（ffmpeg 自带）。

用法：
  1. 编辑下方 SEGS 列表（(段名, 文案) 每段一句/一段话），段名会用于 adelay 偏移与字幕生成
  2. python3 make_tts.py
  3. 输出 audio/{段名}.mp3；同一份 SEGS 会被 make_subs.py 复用来生成字幕

⚠️ 断词铁律（edge-tts 无法按 SSML 控制，只能改文案）：
  - edge-tts 底层把文本经 xml.sax.saxutils.escape 转义后传给微软 TTS，SSML 标签进不去；
  - 零宽连字符 U+2060 也无效（实测 4 个变体时长完全相同）。
  - 想让某个词组连读/纠正多音字，唯一的可靠办法是改写成自然说法：
    · "多运营商"被读成"多 / 运营商"（断词） → 改"多家运营商"即可连读
    · "重传"被读成 zhòngchuán → 改"重新传输"
  - 生成后必须**试听确认**读音正确，别只看文本。
"""
import asyncio, os
import edge_tts

VOICE = "zh-CN-YunjianNeural"  # 沉稳男声；实测断词("多运营商")比云希连贯、"然而"不拖长音
RATE = "+0%"                   # 语速：+8% 略快（如需要）

# ================= 配音文案（叙事定稿后填） =================
# 结构：(段名, 文案)。段名=adelay 偏移与字幕切条共用 key；顺序=播放顺序。
SEGS = [
    ("seg0_title", "这里是片头主标题，一句话介绍项目。"),                # 片头
    ("seg1_bg", "这是背景段，讲应用场景和为什么要做这件事。"),          # 背景+痛点
    ("seg2_scheme", "这是方案段，讲核心技术原理，如何解决问题。"),      # 方案
    ("seg3_arch", "这是架构段，讲系统架构和数据流走向。"),              # 架构
    ("seg4_feedback", "这是反馈闭环段，讲机制如何闭环。"),              # 反馈
    ("seg5_demo", "下面展示实测效果。机载端回传的视频经编码和公网传输，地面站解码播放稳定流畅。"),  # 实测
    # 结束页如需配音可加
]
# ==========================================================


def main():
    os.makedirs("audio", exist_ok=True)
    for name, txt in SEGS:
        out = f"audio/{name}.mp3"
        asyncio.run(edge_tts.Communicate(txt, VOICE).save(out))
        print(f"OK {name} <- {out}")

    print("\n配音生成完毕。把每段时长（ffprobe 查）累加成画面段边界（秒），"
          "再按累积毫秒偏移写进 build_video.sh 的 adelay；"
          "同一份 SEGS 会被 make_subs.py 复用来生成字幕。")


if __name__ == "__main__":
    main()
