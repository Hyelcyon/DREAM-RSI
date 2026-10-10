<div align="center">

[English](../../README.md) · [한국어](README_kr.md) · [日本語](README_jp.md) · **中文**

# DREAM-RSI: 递归自我改进引擎

### 面向 AI Agent 的离线蒙特卡洛回放与搜索策略优化 MCP 服务器

**将历史探索树模拟为虚拟环境，零外部 Token 消耗实现离线策略优化。**

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-8_tools_%7C_2_resources-5c4ee5?style=flat-square)](../mcp-contracts.md)
[![Type Checked](https://img.shields.io/badge/types-pyright_strict-blue?style=flat-square)](../../pyrightconfig.json)
[![Tests](https://img.shields.io/badge/tests-23%20passed-success?style=flat-square)](../../tests)
[![License: MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](../../LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2609.14858-B31B1B?style=flat-square)](https://arxiv.org/abs/2609.14858)

[快速上手](#快速上手) · [工作原理](#工作原理) · [MCP 工具](#mcp-工具) · [数理模型](#数理模型) · [开发与验证](#开发与验证) · [引用](#引用)

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
