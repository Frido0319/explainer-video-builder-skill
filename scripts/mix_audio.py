#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定性混音：按时间轴放置各段配音 + 混入背景乐 → full_audio.wav。
替代 ffmpeg amix（4.2.7 的 amix 按"活跃输入数"动态归一化，对不重叠音轨会
造成响度阶梯递增——seg0_title≈-25dB 一路涨到 seg5_demo≈-9dB，demo 段突然变吵）。

本脚本用 numpy 把每段解码为 44.1k PCM，按 SEG_STARTS 放置在静音时间轴上，
全程无自动增益，各段保持原始相对电平 → 全片响度一致。

坑：配音段 mp3 是单声道，若用 ffmpeg `-ac 2` 转立体声，swresampler 会把每声道
幅度减半（能量分到两声道，正好 -3dB），全片被白吞 3dB。因此配音段按单声道
解码，同一份样本原幅度写入 L/R 两声道；背景乐本就是立体声，走立体声解码。
用法: python3 mix_audio.py <END_END>  （END_END=总时长秒）
"""
import sys, subprocess, wave
import numpy as np
from make_tts import SEGS

SR = 44100

# 与 build_video.sh 时间轴一致的各段起始秒
SEG_STARTS = {
    "seg0_title":   0.0,
    "seg1_bg":      5.6,
    "seg2_scheme":  24.4,
    "seg_compare":  46.0,
    "seg_innov":    67.0,
    "seg3_arch":    89.0,
    "seg4_feedback": 112.0,
    "seg5_demo":    124.5,
}
BGM_VOL = 0.11   # 背景乐 bed（与原 amix 后等效电平一致，≈-53.6dB，低于人声 30dB）
FADE_DUR = 2.85  # 结尾淡出时长（s）

def decode_mono(path):
    """ffmpeg 解码为 44.1k 单声道 float32 一维数组（配音段用，避免 -ac 2 的 -3dB 增益损失）"""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32)

def decode_stereo(path):
    """ffmpeg 解码为 44.1k 立体声 float32 ndarray（背景乐用，双声道直通无增益损失）"""
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path,
         "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2)

def main():
    end = float(sys.argv[1]) if len(sys.argv) > 1 else 157.124
    n = int(round(end * SR))
    mix = np.zeros((n, 2), dtype=np.float64)

    # 1) 放置各段配音（单声道 → 原幅度写进 L/R 两声道）
    for name, _ in SEGS:
        a = decode_mono(f"audio/{name}.mp3")
        off = int(round(SEG_STARTS[name] * SR))
        stop = min(n, off + len(a))
        if stop > off:
            mix[off:stop, 0] += a[: stop - off]
            mix[off:stop, 1] += a[: stop - off]
        print(f"  放置 {name} @{SEG_STARTS[name]:.1f}s  len={len(a)/SR:.2f}s")

    # 2) 背景乐循环铺满全片（立体声）
    bgm = decode_stereo("audio/bgm.wav")
    bg_idx = 0
    for i in range(n):
        mix[i] += bgm[bg_idx] * BGM_VOL
        bg_idx += 1
        if bg_idx >= len(bgm):
            bg_idx = 0

    # 3) 结尾淡出
    f0 = int(round((end - FADE_DUR) * SR))
    if f0 < n:
        fade = np.linspace(1.0, 0.0, n - f0, dtype=np.float64)[:, None]
        mix[f0:] *= fade

    # 4) 削波保护
    peak = float(np.abs(mix).max())
    if peak > 0.99:
        mix *= 0.99 / peak
        print(f"  峰值 {peak:.3f} >0.99，整体衰减到 0.99")
    else:
        print(f"  峰值 {peak:.3f}（未削波）")

    # 5) 写出 full_audio.wav（pcm_s16le）
    data = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open("audio/full_audio.wav", "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"full_audio.wav 写出 {end:.3f}s")

if __name__ == "__main__":
    main()
