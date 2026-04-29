---
name: tao-kb-kg-builder
description: |
  Build and refine Taoist knowledge graphs using Qwen3 Coder.
  
  **Use when:**
  - Annotating new classical texts for the KG
  - Cross-referencing concepts (e.g., "道" across all four classics)
  - Validating semantic consistency in the KG
  - Generating relationship recommendations
  - Identifying gaps or redundancies in the graph
---

# Tao-KB Knowledge Graph Builder

Workflow for iteratively building the Taoist philosophical knowledge graph with Qwen3 Coder.

## Quick Start

1. **Prepare your text**: Select a passage or chapter from the classics
2. **Run the analysis**: `/tao-kg-analyze <text>` to extract KG elements
3. **Review & validate**: Check cross-references and relationships
4. **Update JSON**: Integrate results into `philosophy_kg.json`

## Common Tasks

### 📝 Analyze a New Text

```
/tao-kg-analyze <passage> --source "Daodejing Ch.1" --extraction all
```

Returns: Entities, relations, metaphors, key concepts

### 🔗 Find Cross-References

```
/tao-kg-cross-ref --concept "道" --classics daodejing zhuangzi liezi wenzi
```

Returns: All usages of the concept with context

### ✅ Validate Graph Consistency

```
/tao-kg-validate --domain "taoist-philosophy" --check-types --check-relations
```

Returns: Inconsistencies, missing nodes, suggestions

### 🎯 Generate Relationship Suggestions

```
/tao-kg-suggest-relations --nodes philosophy_kg.json --confidence-threshold 0.8
```

Returns: Recommended new relationships with confidence scores

## Output Format

All outputs are structured as JSON for integration:

```json
{
  "source": "Daodejing Ch.1",
  "entities": [
    {"name": "道", "type": "concept", "definition": "..."}
  ],
  "relations": [
    {"source": "道", "type": "is-concept-of", "target": "宇宙观"}
  ],
  "metaphors": [
    {"term": "玄牝", "interpretation": "..."}
  ]
}
```

## Integration with tao-kb Pipeline

The outputs can be piped directly into:
- `tag_taxonomy.json` - Update tag mappings
- `philosophy_kg.json` - Merge new nodes and relations
- `*.tagged.md` - Annotate source texts
- `zhuangzi_kg.mmd` - Update visual diagrams

## Advanced Options

- `--confidence <0-1>` - Filter results by confidence
- `--depth <1-3>` - Control relationship search depth
- `--language <zh|en>` - Output language
- `--format <json|csv|mermaid>` - Output format
