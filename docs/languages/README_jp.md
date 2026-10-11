<div align="center">

[English](../../README.md) · [한국어](README_kr.md) · **日本語** · [中文](README_cn.md)

# DREAM-RSI: 再帰的自己改善エンジン

### AIエージェントのためのオフライン・モンテカルロ・リプレイ＆探索ポリシー最適化 MCP サーバー

**過去の探索木を仮想環境としてシミュレーションし、トークン消費ゼロで探索ポリシーを最適化します。**

[![Release](https://img.shields.io/github/v/release/Hyelcyon/DREAM-RSI?style=flat&color=cb3837)](https://github.com/Hyelcyon/DREAM-RSI/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Hyelcyon/DREAM-RSI/ci.yml?branch=main&style=flat&label=CI)](https://github.com/Hyelcyon/DREAM-RSI/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-11_tools_%7C_3_resources-5c4ee5?style=flat)](../mcp-contracts.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat)](../../LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2609.14858-B31B1B?style=flat)](https://arxiv.org/abs/2609.14858)

[クイックスタート](#クイックスタート) · [動作原理](#動作原理) · [MCP ツール](#mcp-ツール) · [数理モデル](#数理モデル) · [開発と検証](#開発と検証) · [引用](#引用)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI** は、研究論文 *Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems* (arXiv: 2609.14858) に基づく、独立したクリーンルーム Python 実装です。標準的な Model Context Protocol (MCP) STDIO ワークフローを介して、自律型 AI エージェントに自己改善探索ポリシーの最適化を提供します。

- **外部トークン消費ゼロ**: 蓄積された探索木を仮想リプレイ環境として活用し、外部 LLM の API 呼び出しなしでポリシーを改善します。
- **位相的整合性の保証**: 循環参照の検出とアトミックなファイル書き込みにより、有向非巡回グラフ (DAG) の厳密な整合性を保護します。
- **動的ポートフォリオ最適化**: 幅広い仮説分岐 ($W$) と反復的な深層洗練 ($R$) の間のパレート・フロンティアを計算します。
- **決定論的グリッド計画**: 過去の試行実績に基づき、最適なワーカー割り当てを推薦します。

---

## クイックスタート

### エージェント設定

```json
{
  "mcpServers": {
    "dream-rsi": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"]
    }
  }
}
```

### サーバー起動

```bash
uv run dream-rsi
```

すべてのログは標準エラー出力 (stderr) に送られるため、STDIO 上の JSON-RPC プロトコルが損なわれることはありません。

---

## MCP ツール一覧

| ツール | 説明 |
| :--- | :--- |
| `dream_history_list` | 登録されたすべての探索木とセッションの一覧を取得 |
| `dream_history_get_tree` | 指定した探索木のトポロジーとノード情報を取得 |
| `dream_history_save_node` | 新しい探索試行ノードを保存 |
| `dream_replay_run` | 過去の探索木に対して仮想リプレイを実行 |
| `dream_replay_get_frontier` | パレート・フロンティアを算出 |
| `dream_policy_compare` | 候補ポリシーとベースライン・ポリシーを比較 |
| `dream_policy_plan_grid` | 次の試行のための最適な探索幅 $W$ と深さ $R$ を計画 |
| `dream_status` | エンジンの状態と保存ディレクトリの整合性を確認 |

---

## 開発と検証

```bash
uv sync
uv run pytest
uv run pyright
uv run python scripts/verify_mcp.py
```

---

## ライセンス

MIT ライセンスに基づいて提供されています。
