# Minimal V2 Create Example

This repository-safe example demonstrates `create` mode using only neutral card content:

```bash
python3 -m explainer_video_v2.cli validate examples/create_minimal/project.json
python3 -m explainer_video_v2.cli build examples/create_minimal/project.json
python3 -m explainer_video_v2.cli verify examples/create_minimal/project.json
```

Generated files are written to `examples/create_minimal/output/` and are ignored by Git.
