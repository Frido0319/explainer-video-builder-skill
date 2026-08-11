# SVG 技术图：Flat Icon 规范（1920 画布）

规范来源：高星 skill `fireworks-tech-graph` 的 `style-1-flat-icon.md`，按 1920×1080 画布放大 2x 应用。参考成品：`arch.svg`（系统架构）、`feedback.svg`（反馈闭环）——两者同风格、同参数。

## 配色

```
背景/节点填充   #ffffff
节点边框        #d1d5db 1.5px（1920 画布用 3px）
圆角            rx=8（组件）、rx=16（区域框）
主文字          #111827
次要文字        #6b7280
主流程箭头      #2563eb（蓝-600）
反馈/备用箭头   #dc2626（红-600，虚线）
数据/成功       #16a34a（绿-600）
异步            #9333ea（紫-600）
图标 tint 底色  #eff6ff 蓝 / #fef2f2 红 / #fff7ed 橙 / #f3f4f6 灰
区域框浅底      #f5f9ff（蓝） / #fafafa（灰）
分隔线          #e5e7eb 1.5px
```

## 组件规格（1920 画布）

- 组件框 400×96，白底、`#d1d5db` 3px 细边框、`rx=8`。
- 组件内：左侧 44×44 `rx=10` tint 色图标，右侧两行文字——标题 28px Bold `#111827`，副标题 22px `#6b7280`。
- 组件间距 ≥64px；所有坐标对齐 8px 网格。
- 中心列：公网区组件用 240 宽（如"花生壳服务"），居中。

## 图标（SVG path 手绘，不引外部图片）

常用简单几何，均 44×44 容器内、tint 底：

| 语义 | 画法 |
|---|---|
| 相机 | 圆角矩形 + 内圆 |
| 波形/编码 | 波浪 path + 三个小圆点 |
| 分片/打包 | 三个小方块 |
| 地球/服务 | 圆 + 水平/垂直椭圆线 |
| 显示器 | 圆角矩形 + 底座线 |
| 勾/校验 | 圆角矩形 + 对勾 path |
| 拼图/重组 | 交错线段 + 中心块 |
| 统计 | 三根竖条柱 |

## 区域框（三列布局）

- 发送端 / 公网 / 接收端三大列，各一个浅 tint 大框：`rx=16`、`#d1d5db` 1.5px 细边框、内部 28px 区域标题（发送/接收端用蓝 `#2563eb`，公网用灰 `#6b7280`）。
- 发送端、接收端组件镜像布局（发送自底向上、接收自顶向下，或对齐到同一条 y 走廊）。

## 通道走线

- 主流程：`#2563eb` 3px 实线；反馈：`#dc2626` 3px 虚线 `stroke-dasharray="16,12"`。
- **正交走线**：`M 起点x,起y L ...` 走水平+垂直拐角，不画斜线。
- 跨线标签：白底小圆角矩形 `(rx=6, 边框 #e5e7eb)` 遮断下方线段，再叠 24px Bold 通道名，避免"线穿字"。
- 箭头 marker：`<marker>` 三角，`refX=13 refY=8`，颜色同线色。

## 渲染

- 直接浏览器渲染最准。chrome headless：
  ```bash
  google-chrome --headless --screenshot=out.png --window-size=1920,1080 --default-background-color=00000000 file.svg
  ```
  或 `chromium --headless=new --screenshot=...`。rsvg-convert 对字体/文本基线偏差大，仅作后备。
- SVG 文件头部加 `<font-family="Noto Sans CJK SC, sans-serif">`，确保中文。
