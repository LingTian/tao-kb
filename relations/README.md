# 二层关系补标说明

本目录用于存放 `tao-kb` 的二层关系标注数据（在一层实体/概念标注基础上追加）。

## 当前文件

- `secondary_relations.json`：从 `chapters/**/*.tagged.md`（排除 `legacy`）自动生成的二层关系数据。

## 关系类型（当前规则法）

- `contrast`：由 `〖@对立:a|b〗` 直接抽取的显式对立关系
- `causal_hint`：句内出现“故/所以/则/因/是以”等关键词时的因果提示关系
- `progression_hint`：句内出现“而后/然后/乃/遂”等关键词时的递进提示关系
- `co_occurs`：同一句内多标签共现关系

## 生成方式

```bash
python3 scripts/build_secondary_relations.py
```

## 注意

- 这是“补标第一版”（规则法），适合做关系发现和人工复核入口。
- `contrast` 置信度较高；`causal_hint` 与 `progression_hint` 为弱监督提示；`co_occurs` 适合图谱探索，不等于强语义关系。
