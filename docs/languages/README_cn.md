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

[English](../../README.md) · [한국어](README_kr.md) · [日本語](README_jp.md) · **中文**

# DREAM-RSI: 递归自我改进引擎

### 面向 AI Agent 的离线蒙特卡洛回放与搜索策略优化 MCP 服务器

**将历史探索树模拟为虚拟环境，零外部 Token 消耗实现离线策略优化。**

[![Release](https://img.shields.io/github/v/release/Hyelcyon/DREAM-RSI?style=flat&color=cb3837)](https://github.com/Hyelcyon/DREAM-RSI/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Hyelcyon/DREAM-RSI/ci.yml?branch=main&style=flat&label=CI)](https://github.com/Hyelcyon/DREAM-RSI/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-11_tools_%7C_3_resources-5c4ee5?style=flat)](../mcp-contracts.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat)](../../LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2609.14858-B31B1B?style=flat)](https://arxiv.org/abs/2609.14858)

[快速上手](#快速上手) · [MCP 工具](#mcp-工具) · [数理模型](#数理模型) · [开发与验证](#开发与验证) · [FAQ](#faq) · [引用](#引用)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI** 是基于研究论文 *Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems* (arXiv: 2609.14858) 构建的 Python 搜索策略优化引擎，通过 Model Context Protocol (MCP) STDIO 服务器对外提供能力。

自主 AI Agent 在探索算法合成、数学优化或系统代码编写时，会生成庞大的试错搜索树。在在线环境中直接评估新的搜索策略会导致持续的 Token 消耗与环境交互开销。DREAM-RSI 将**在线树扩展**与**离线策略评估**解耦：

1. **将探索树作为虚拟仿真器**：历史执行轨迹构成包含执行结果与验证信号的有向无环图 (DAG)。回放引擎无需调用外部 LLM 即可将历史探索树作为仿真环境。
2. **离线回放 ("Dreaming")**：替代搜索策略在图上重放历史状态-动作转移，以评估不同探索-利用平衡点 ($\beta$) 的表现。
3. **多目标前沿评估**：利用帕累托效率指标计算探索广度 ($W$) 与精炼深度 ($R$) 之间的实证权衡。
4. **递归式搜索策略改进**：由离线回放推荐的策略指导后续在线探索轮次，为未来的回放周期沉淀更丰富的探索树。

---

## 快速上手

### Agent 配置

#### 自动跨客户端配置

```bash
uv run python scripts/configure_clients.py --all
```

#### 手动配置 (Claude Desktop / Claude Code / Codex)

Claude (`claude_desktop_config.json` 或 `.mcp.json`):

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

### 启动服务

```bash
uv run dream-rsi
```

所有诊断信息均输出至标准错误流 (stderr)，确保 STDIO 上的 JSON-RPC 传输通道严谨完好。

---

## MCP 工具列表

| 工具名 | 说明 |
| :--- | :--- |
| `dream_history_list` | 列出所有已注册的发现树与会话 |
| `dream_history_get_tree` | 获取指定树的完整拓扑结构与节点数据 |
| `dream_history_save_node` | 持久化存储单次在线探索尝试节点 |
| `dream_replay_run` | 针对历史发现树执行策略离线虚拟回放 |
| `dream_replay_get_frontier` | 评估所有历史树并生成帕累托前沿 |
| `dream_policy_compare` | 对比候选策略与基线策略的表现 |
| `dream_policy_plan_grid` | 确定性规划下一次任务的搜索广度 $W$ 与深度 $R$ |
| `dream_policy_select_beta` | 基于历史趋势与前沿计算下周期 Beta 自适应值 |
| `dream_benchmark_evaluate` | 在科学发现基准任务上验证候选解 |
| `dream_benchmark_create_tree` | 实例化基准测试发现树并存入本地存储 |
| `dream_status` | 检查引擎运行状态与存储完整性 |

---

## 数理模型

### 探索与利用的权衡 ($\beta$)

动态投资组合策略根据候选质量得分和利用因子 $\beta \in [0, 1]$ 对动作进行采样：

$$P(\text{refine} \mid \text{node}_i) \propto \exp\left(\frac{\beta \cdot \text{score}_i}{\tau}\right)$$

- $\beta \to 0$：策略侧重于在未验证分支上进行广泛的多样性采样。
- $\beta \to 1$：策略将计算资源集中于精炼高分候选节点。

### 搜索网格优化 $(W, R)$

在给定 Worker 预算 $B$ 的情况下，规划分支广度 $W$ 与精炼深度 $R$ 之间的资源分配：

$$W \cdot R \le B, \quad \max_{W, R} \mathbb{E}\left[\max_{i \le W} S_i^{(R)}\right]$$

---

## 开发与验证

```bash
uv sync
uv run pytest
uv run pyright
uv run python scripts/verify_mcp.py
```

---

## FAQ

<details>
<summary><strong>支持哪些 AI Agent？</strong></summary>

支持所有通过 STDIO 实现 Model Context Protocol (MCP) 的 Agent，包括 Claude Code、Google Antigravity、Cursor、OpenAI Codex 等。
</details>

<details>
<summary><strong>离线回放需要外部 LLM 调用或网络访问吗？</strong></summary>

不需要。离线回放使用在线会话期间记录的历史执行图和确定性验证 Oracle，在没有外部网络请求或大语言模型推理的情况下以数学方式评估策略。
</details>

<details>
<summary><strong>探索树如何存储？</strong></summary>

保存在 `DREAM_RSI_STORE_DIR` 或 `data/trees/` 目录下的本地 JSON 文件中。
</details>

<details>
<summary><strong>网格规划中的 W 和 R 代表什么？</strong></summary>

$W$ 代表并行探索 Worker 数量或假设分支数量，$R$ 代表每个分支的精炼深度或迭代预算。网格规划器在总预算 $B$ 限制下优化此权衡。
</details>

---

## 引用

如果您在研究或 Agent 工作流中引用 DREAM-RSI，请引用以下基础论文：

```bibtex
@article{zheng2026dreamrsi,
  title={Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems},
  author={Zheng, Kid and collaborators},
  journal={arXiv preprint arXiv:2609.14858},
  year={2026}
}
```

---

## 开源许可

本项目采用 MIT 许可证。
