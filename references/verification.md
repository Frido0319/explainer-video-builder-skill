# 无视觉自检验证

无图形界面环境下，用"像素采样 + OCR + 坐标审查"代替眼睛。参考脚本：`../scripts/verify_video.py`、`../scripts/check_blackscreen.py`。

## 1. 成品基础校验（ffprobe）

```bash
ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 成品.mp4
ffprobe -v error -select_streams v -show_entries stream=width,height,codec_name -of csv 成品.mp4
ffprobe -v error -select_streams a -show_entries stream=codec_name,sample_rate -of csv 成品.mp4
```
- 时长应等于 `END_END`；分辨率 1920×1080；视频 H.264，音频 AAC。

## 2. 抽帧 + 像素亮度采样

```bash
ffmpeg -y -ss <T> -i 成品.mp4 -frames:v 1 -q:v 2 /tmp/frame_T.png
```

用 PIL 采样判断：
- **黑屏检测**：把画面按行采样亮度。真实演示视频若某个时间点起**上部亮度骤降**（如 75→0），就是黑屏段起点。黑屏起点 = 可用的最晚干净帧。
  ```python
  im = Image.open(f).convert("L")
  top = im.crop((0, 0, w, int(h*0.35))).getextrema()  # 上部亮度范围
  ```
- **页面空白检查**：整图采样，学术卡应接近纯白（如 250+）；预告卡应接近深色渐变。

## 3. OCR 检查文字

```bash
tesseract /tmp/frame_T.png /tmp/ocr_T -l chi_sim 2>/dev/null
```
- 检查标题/要点完整出现、无乱码、无重叠（重叠会 OCR 成乱串）。
- 无 chi_sim 语言包先装：`sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim`。

## 4. 坐标逻辑审查（SVG 图）

- 对 `arch.svg` / `feedback.svg` 这类手写图，用 PIL 在**已知坐标**采样验证：某通道 y 行应只有箭头色（如 `#2563eb`），标签矩形区应有白底遮断。
- 检查走线是否穿字：沿通道 y 扫描，被标签矩形覆盖的区间外不应有文字像素与线重叠。
- 审查要点：网格对齐（坐标 %8==0）、组件间距 ≥64、图标在 44×44 内、两行文字基线不叠。

## 5. 逐段边界抽查

在每段边界前后各抽 1 帧（如 `t-0.3 / t+0.3`），确认淡入淡出正常、切换画面是预期卡片。尤其检查：
- 实测段结束点恰好 = 黑屏起点前（若放过了黑屏，观众会看到黑屏）。
- 结束页在总长窗口内出现（上一版 bug：实测段超时把结束页挤出截断窗口）。
