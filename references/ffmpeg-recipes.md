# ffmpeg 合成配方（时间轴合成 + 字幕烧录 + 坑）

参考成品：`build_video.sh`（智信2026 演示，157s，10 段，带中文字幕）。

## 0. 时间轴先算好

- 用秒做单位，配音偏移用毫秒。
- 画面段边界：`TITLE_END / BG_END / ... / DEMO_END / END_END`，全部在脚本顶部定义，段长由相邻边界相减（用 `python3 -c` 算，避免手算出错）。
- 实测段起点/时长单独定义：`S_DEMO_START`、`S_DEMO_DUR`（时长 = 黑屏起点前的干净段长）。

## 1. 静态卡 → 独立段

```bash
ffmpeg -y -loop 1 -i cards/01_title.png -t 5.2 \
  -vf "fade=t=in:st=0:d=0.4,fade=t=out:st=4.2:d=1.0" \
  -r 25 -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -an seg/01_title.mp4
```
- 无 zoompan 抖动——卡片静态，靠淡入淡出转场。
- 出淡出时 `st = 段长 - 1.0`。

## 2. 实测段（真实视频，最易出错）

**竖屏视频等比居中 + 两侧深色渐变背景**（不裁剪主体、不模糊）：

```bash
ffmpeg -y -i "$RAW_DEMO" -loop 1 -i cards/demo_bg.png \
  -filter_complex "\
[0:v]scale=-1:1080:flags=lanczos[fg];\
[1:v]scale=1920:1080[bg];\
[bg][fg]overlay=x=(W-w)/2:y=0,fade=t=in:st=0:d=0.4" \
  -r 25 -t "$S_DEMO_DUR" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -an \
  seg/08_demo.mp4
```

> **`-t` 必须作为输出选项放在输出文件之前**。放在 `-i` 之间会被当作输入选项，不生效——实测段会跑到源视频全长，把后续段挤出总长窗口（表现为结束页消失）。

- 源视频先做黑屏检测（见 `verification.md`），`S_DEMO_DUR` 取干净段长，**宁短勿长**。

## 3. 多段配音合成音轨（确定性 numpy 混音，勿用 amix）

**用 `scripts/mix_audio.py`（确定性混音器）代替 ffmpeg amix**：按时间轴把各段配音解码为 PCM 放置到静音底，全程无自动增益 → 全片响度一致。

```bash
python3 mix_audio.py "$END_END"     # 读 make_tts.SEGS + SEG_STARTS → audio/full_audio.wav
```

`mix_audio.py` 做的事：单声道解码各配音段 → 原幅度写入 L/R 两声道 → 按 `SEG_STARTS` 放置在时间轴 → 混入立体声背景乐 bed（`BGM_VOL` 调音量）→ 结尾 `afade` 淡出 → 峰值 >0.99 才整体衰减（削波保护）。

**为什么不用 ffmpeg `amix`**：4.2.7 的 amix 按"活跃输入数"动态归一化（`normalize` 选项 4.4 才加入），对**不重叠**的音轨会形成响度阶梯——seg0≈-25dB 一路涨到 demo 段≈-9dB，实测段突然变响变"杂"。

**`-ac 2` 单声道→立体声的 -3dB 坑**：配音段 mp3 是单声道，若用 `-ac 2` 转立体声，swresampler 把能量分到两声道、每声道幅度减半（正好 -3dB），全片被白吞 3dB。解法：配音段按单声道解码（`-ac 1`），同一份样本原幅度写入 L/R；背景乐本就是立体声，`-ac 2` 直通无损。

（旧 amix 配方仅作参考，勿直接复用：`aresample=44100 + aformat=channel_layouts=stereo + adelay=偏移|偏移 → amix=duration=longest:dropout_transition=0 + volume=N 补偿 + apad=whole_dur=$END_END`）

## 5. 拼接画面 + 合成最终视频

```bash
# concat 需要绝对路径文件列表（-safe 0）
printf "file '%s'\n" $(pwd)/seg/*.mp4 > seg/concat.txt   # 按 01..09 顺序
ffmpeg -y -f concat -safe 0 -i seg/concat.txt -c copy seg/video_only.mp4
```

### 5.5 字幕烧录（最终合成，必须重编码）

字幕是**必须项**。用 `make_subs.py` 生成 `subs.srt` 后，烧录必须**重编码**（不能 `-c:v copy`）：

```bash
ffmpeg -y -i seg/video_only.mp4 -i audio/full_audio.wav \
  -vf "subtitles=subs.srt:force_style='FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=2,Alignment=2'" \
  -map 0:v -map 1:a -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k \
  -movflags +faststart -t "$END_END" 成品.mp4
```

- **绝不能加 `MarginV=45`**：实测 ffmpeg 4.2.7 + libass 下，force_style 里含 MarginV=45 会导致**字幕完全不渲染**（成片整帧 0 暗像素）。去掉 MarginV 后正常。
- 字幕烧录后实际占 **y960-1049**，所以卡片内容最下缘要压到 ≤y940（见 cards.md）。
- 8 位色值 + `Shadow=2` + `Alignment=2`（底部居中）在此版本 libass 正常。
- 输出 H.264 + AAC + faststart，1920×1080 yuv420p。

## 6. 视频打不开（GStreamer 解码器缺失）

totem/播放器报"缺少插件"打不开 H.264/AAC MP4，装（Ubuntu）：

```bash
sudo apt-get install -y gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
```

装完 `gst-inspect-1.0 avdec_h264 avdec_aac` 应能列出解码器。
