# Minimal V2 Enhance Example

This repository-safe example demonstrates `enhance` mode without embedding any user project content. Use an input video that is at least eight seconds long:

```bash
export V2_SOURCE_VIDEO="/path/to/source.mp4"
export V2_OUTPUT_DIR="/path/to/output"
python3 -m explainer_video_v2.cli validate examples/enhance_minimal/project.json
python3 -m explainer_video_v2.cli build examples/enhance_minimal/project.json
python3 -m explainer_video_v2.cli verify examples/enhance_minimal/project.json
```

The source is read-only. Generated media and caches are written under `V2_OUTPUT_DIR`.
