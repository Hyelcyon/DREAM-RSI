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

[快速上手](#快速上手) · [MCP 工具](#mcp-工具) · [数理模型](#数理模型) · [开发与验证](#开发与验证) · [引用](#引用)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI** 是基于论文 *Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems* (arXiv: 2609.14858) 构建的独立纯净室（Cleanroom）Python 实现。它通过标准 Model Context Protocol (MCP) STDIO 工作流，为自主 AI Agent 赋予递归自我改进与搜索策略优化能力。

- **零额外 Token 开销**：将已沉淀的历史发现树作为离线虚拟仿真环境，无需调用任何外部 LLM API。
- **严格的拓扑无环性**：内置环路检测算法与原子化 JSON 持久化，确保有向无环图 (DAG) 状态严谨可靠。
- **动态投资组合策略**：平衡假设分支广度 ($W$) 与深度迭代精炼 ($R$) 之间的帕累托前沿（Pareto Frontier）。
- **确定性网格规划**：根据实证回放性能，自适应规划后续轮次的探索资源与探测上限。

---

## 快速上手

### Agent 配置

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

## 开发与验证

```bash
uv sync
uv run pytest
uv run pyright
uv run python scripts/verify_mcp.py
```

---

## 开源许可

本项目采用 MIT 许可证。
