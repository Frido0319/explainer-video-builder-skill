# V2 精剪原型

本目录只存在于 `v2-prototype-editing` 支线，用于验证已有视频的画面精剪能力。稳定版 `main` 不包含这些原型文件。

## 构建

```bash
cd explainer-video-builder-skill
export AUTOMOTIVE_RAG_DELIVERY="/path/to/06_视频成果"
python3 prototypes/v2_editing/build_prototype.py
```

构建脚本读取 `timeline.json`，从原视频 `36–64s` 生成两支28秒样片：

- `原版片段_36-64s.mp4`
- `V2精剪样片_平滑推进版_36-64s.mp4`

旧的 `V2精剪样片_36-64s.mp4` 保留为整数像素裁切抖动问题的对照，不再由当前构建脚本覆盖。平滑版会先用 Lanczos 把画面预放大到 7680×4320，再执行动态裁切，减少 ffmpeg 4.2.7 `zoompan` 的整数坐标跳动。

输出位置：

`${AUTOMOTIVE_RAG_DELIVERY}/v2_prototype/`

## 验证

```bash
python3 -m unittest tests.test_v2_timeline -v
python3 prototypes/v2_editing/verify_prototype.py
```

验证内容包括：

- 时间轴与缩放上限；
- ASS字幕截取和时间重定时；
- 1920×1080、H.264 + AAC、28秒时长；
- 音轨非静音且与原版响度一致；
- 章节提示、四组标注和动态推近能在代表帧中检测到；
- 中文字幕在底部安全区域正常出现；
- 生成原版/V2逐帧对比接触表。

生成的 MP4、接触表与验证报告属于项目交付产物，不提交到本 Skill 仓库。
