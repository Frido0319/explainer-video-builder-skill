# Automotive RAG V2 Enhance Example

This example reproduces the approved 72-second automotive RAG showcase with the generic V2 engine.

The manifest deliberately uses `AUTOMOTIVE_RAG_DELIVERY` instead of committing machine-specific absolute paths. Point it at the existing `06_视频成果` directory before running:

```bash
export AUTOMOTIVE_RAG_DELIVERY="/path/to/06_视频成果"
python3 -m explainer_video_v2.cli validate examples/automotive_rag/project.json
python3 -m explainer_video_v2.cli build examples/automotive_rag/project.json
python3 -m explainer_video_v2.cli verify examples/automotive_rag/project.json
```

The builder reads the original MP4 files without modifying them and writes generated files under `$AUTOMOTIVE_RAG_DELIVERY/v2_manifest/`.
