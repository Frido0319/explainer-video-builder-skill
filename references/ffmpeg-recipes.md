# ffmpeg 合成配方（时间轴合成 + 坑）

参考成品：`build_video.sh`（智信2026 演示，107s，9 段）。

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

## 3. 多段配音合成音轨

```bash
ffmpeg -y \
  -i audio/seg0.mp3 -i audio/seg1.mp3 ... \
  -filter_complex "\
[0:a]aresample=44100,aformat=channel_layouts=stereo,adelay=0|0[v0];\
[1:a]aresample=44100,aformat=channel_layouts=stereo,adelay=5260|5260[v1];\
...
[v0][v1][...]amix=inputs=6:duration=longest:dropout_transition=0,volume=6.0,apad=whole_dur=$END_END[a]" \
  -map "[a]" -t "$END_END" -c:a pcm_s16le audio/voice_track.wav
```

- 每段统一 `aresample=44100` + `aformat=channel_layouts=stereo`，否则 amix 报错或声道不一致。
- `adelay=偏移|偏移`（左右声道都加）。
- `amix` 音量会除 N，`volume=6.0` 补偿（N=6 时）；`apad=whole_dur=总长` 补齐静音尾巴。

## 4. 混背景乐 + 防削波

```bash
ffmpeg -y -i audio/voice_track.wav -i audio/bgm.wav \
  -filter_complex "\
[0:a]volume=2.0[v];\
[1:a]volume=0.22[bg];\
[v][bg]amix=inputs=2:duration=first:dropout_transition=0,\
afade=t=out:st=$END_END-2.85:d=2.85,\
alimiter=limit=0.95:level=disabled[a]" \
  -map "[a]" -t "$END_END" -c:a pcm_s16le audio/full_audio.wav
```

- 背景乐音量压到配音之下（约 0.22 vs 2.0）。
- 结尾 `afade` 淡出；**最后 `alimiter=limit=0.95` 防削波**——多路叠加必加，否则爆音。

## 5. 拼接画面 + 合成最终视频

```bash
# concat 需要绝对路径文件列表（-safe 0）
printf "file '%s'\n" $(pwd)/seg/*.mp4 > seg/concat.txt   # 按 01..09 顺序
ffmpeg -y -f concat -safe 0 -i seg/concat.txt -c copy seg/video_only.mp4

ffmpeg -y -i seg/video_only.mp4 -i audio/full_audio.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
  -movflags +faststart -t "$END_END" 成品.mp4
```

- 输出 H.264 + AAC + faststart，1920×1080 yuv420p。

## 6. 视频打不开（GStreamer 解码器缺失）

totem/播放器报"缺少插件"打不开 H.264/AAC MP4，装（Ubuntu）：

```bash
sudo apt-get install -y gstreamer1.0-libav gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
```

装完 `gst-inspect-1.0 avdec_h264 avdec_aac` 应能列出解码器。
