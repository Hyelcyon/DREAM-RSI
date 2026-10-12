<div align="center">

<p>
  <img src="../../assets/logos/google.svg" alt="Google" height="26" align="middle">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../../assets/logos/google-deepmind-dark.svg">
    <img src="../../assets/logos/google-deepmind-light.svg" alt="Google DeepMind" height="22" align="middle">
  </picture>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../../assets/logos/umd-dark.svg">
    <img src="../../assets/logos/umd-light.svg" alt="University of Maryland, College Park" height="26" align="middle">
  </picture>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="../../assets/logos/uva-dark.svg">
    <img src="../../assets/logos/uva-light.svg" alt="University of Virginia" height="28" align="middle">
  </picture>
</p>

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

[クイックスタート](#クイックスタート) · [MCP ツール](#mcp-ツール) · [数理モデル](#数理モデル) · [開発と検証](#開発と検証) · [FAQ](#faq) · [引用](#引用)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI** は、研究論文 *Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems* (arXiv: 2609.14858) に基づく Python 検索ポリシー最適化エンジンであり、Model Context Protocol (MCP) STDIO サーバーとして動作します。

自律型エージェントがアルゴリズム合成、数理最適化、システムコード作成を探索する際、膨大な試行錯誤の木が生成されます。新しい探索ポリシーをオンラインで直接評価することは、継続的なトークン消費と環境との対話を要求します。DREAM-RSI は**オンラインの探索木拡張**と**オフラインのポリシー評価**を分離します:

1. **仮想シミュレータとしての探索木**: 過去の実行トレースを実行結果および検証シグナルを含む有向非巡回グラフ (DAG) としてモデル化します。リプレイエンジンは外部 LLM の呼び出しなしで過去の探索木をシミュレーション環境として扱います。
2. **オフラインリプレイ ("Dreaming")**: 代替探索ポリシーがグラフ上で過去の状態・行動遷移を再実行し、様々な探索・活用バランス ($\beta$) のパフォーマンスをシミュレーションします。
3. **多目的フロンティア評価**: パレート効率性指標を使用して、探索の幅 ($W$) と洗練の深さ ($R$) の間の実証的トレードオフを計算します。
4. **再帰的な探索改善**: オフラインリプレイによって推奨されたポリシーが次のオンライン探索ラウンドをスケジュールし、将来のリプレイサイクルのためにより豊かな探索木を蓄積します。

---

## クイックスタート

### エージェント設定

#### 自動クライアント設定

```bash
uv run python scripts/configure_clients.py --all
```

#### 手動設定 (Claude Desktop / Claude Code / Codex)

Claude (`claude_desktop_config.json` または `.mcp.json`):

```json
{
  "mcpServers": {
    "dream-rsi": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"],
      "env": {
        "DREAM_RSI_STORE_DIR": "/absolute/path/to/DREAM-RSI/data/trees"
      }
    }
  }
}
```

OpenAI Codex (`config.toml`):

```toml
[mcp_servers.dream-rsi]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"]
startup_timeout_sec = 60

[mcp_servers.dream-rsi.env]
DREAM_RSI_STORE_DIR = "/absolute/path/to/DREAM-RSI/data/trees"
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
| `dream_policy_select_beta` | 履歴トレンドとフロンティアに基づく次期ベータ適応を計算 |
| `dream_benchmark_evaluate` | 科学的発見ベンチマーク問題で候補解を検証 |
| `dream_benchmark_create_tree` | ベンチマーク検証用の仮想探索木を生成 |
| `dream_status` | エンジンの状態と保存ディレクトリの整合性を確認 |

---

## 数理モデル

### 探索と活用のバランス ($\beta$)

動的ポートフォリオポリシーは、候補の品質スコアと活用係数 $\beta \in [0, 1]$ に基づいて行動をサンプリングします:

$$P(\text{refine} \mid \text{node}_i) \propto \exp\left(\frac{\beta \cdot \text{score}_i}{\tau}\right)$$

- $\beta \to 0$: 未検証の分岐に対する多様な探索を重視します。
- $\beta \to 1$: 高スコアの候補ノードを深く洗練することに計算を集中させます。

### 探索グリッドの最適化 $(W, R)$

総ワーカー予算 $B$ が与えられたとき、分岐幅 $W$ と洗練深度 $R$ の最適な配分を算出します:

$$W \cdot R \le B, \quad \max_{W, R} \mathbb{E}\left[\max_{i \le W} S_i^{(R)}\right]$$

---

## 開発と検証

```bash
uv sync
uv run pytest
uv run pyright
uv run python scripts/verify_mcp.py
```

---

## FAQ

<details>
<summary><strong>どのエージェントで利用できますか？</strong></summary>

STDIO 経由の Model Context Protocol (MCP) をサポートする任意のエージェント (Claude Code、Google Antigravity、Cursor、OpenAI Codex など) で利用可能です。
</details>

<details>
<summary><strong>オフラインリプレイに外部 LLM 呼び出しやネットワークアクセスは必要ですか？</strong></summary>

いいえ。オンラインセッション中に記録された過去の実行グラフと決定論的検証オラクルを使用するため、外部ネットワーク要求や LLM プロンプトなしにポリシーを評価します。
</details>

<details>
<summary><strong>探索木はどのように保存されますか？</strong></summary>

`DREAM_RSI_STORE_DIR` または `data/trees/` 配下のローカル JSON ファイルとして保存されます。
</details>

<details>
<summary><strong>グリッド計画における W と R は何を表していますか？</strong></summary>

$W$ は並行探索ワーカー数または仮説分岐数を表し、$R$ は分岐ごとの洗練深度または試行予算を表します。グリッドプランナーは総予算 $B$ の下でこのトレードオフを最適化します。
</details>

## 引用

研究またはエージェントのワークフローにおいて DREAM-RSI を引用する場合は、以下の原著論文を参照してください:

```bibtex
@article{zheng2026dreamrsi,
  title={Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems},
  author={Zheng, Kid and collaborators},
  journal={arXiv preprint arXiv:2609.14858},
  year={2026}
}
```

---

## ライセンス

MIT ライセンスに基づいて提供されています。
