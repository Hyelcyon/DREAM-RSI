<div align="center">

[English](../../README.md) · **한국어** · [日本語](README_jp.md) · [中文](README_cn.md)

# DREAM-RSI: 재귀적 자기 개선 엔진

### AI 에이전트를 위한 오프라인 몬테카를로 리플레이 및 탐색 정책 최적화 MCP 서버

**과거 탐색 트리를 가상 환경으로 시뮬레이션하여 토큰 소모 없이 정책을 최적화합니다.**

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-8_tools_%7C_2_resources-5c4ee5?style=flat-square)](../mcp-contracts.md)
[![Type Checked](https://img.shields.io/badge/types-pyright_strict-blue?style=flat-square)](../../pyrightconfig.json)
[![Tests](https://img.shields.io/badge/tests-23%20passed-success?style=flat-square)](../../tests)
[![License: MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](../../LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2609.14858-B31B1B?style=flat-square)](https://arxiv.org/abs/2609.14858)

[빠른 시작](#빠른-시작) · [작동 원리](#작동-원리) · [MCP 도구 목록](#mcp-도구-목록) · [수학적 정식화](#수학적-정식화) · [개발 및 검증](#개발-및-검증) · [인용](#인용)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI**는 연구 논문 *Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems* (arXiv: 2609.14858)의 정책 최적화 프레임워크를 기반으로 개발된 독립적인 클린룸(Cleanroom) Python 구현체입니다. 표준 Model Context Protocol (MCP) STDIO 워크플로를 통해 AI 에이전트에 자율적 자기 개선 기능을 제공합니다.

자율 AI 에이전트는 코드, 수학, 과학적 가설 탐색과 같은 고차원 공간을 지속적으로 탐색합니다. 기존 탐색 방식은 저조한 후보군에 연산 비용을 낭비하거나 메타 계획을 위해 외부 LLM API를 호출하여 막대한 토큰을 낭비합니다. DREAM-RSI는 **온라인 실제 탐색(Online Discovery)**과 **오프라인 정책 개선(Offline Dreaming)**을 완전히 분리합니다:

- **외부 토큰 소비 제로**: 저장된 탐색 트리를 가상 실행 환경으로 활용하여 외부 LLM 호출 없이 오프라인 정책을 최적화합니다.
- **엄격한 위상 무결성**: 순환 참조 방지(Cycle Detection) 알고리즘과 원자적(Atomic) 파일 저장을 통해 방향성 비순환 그래프(DAG)를 유지합니다.
- **동적 포트폴리오 최적화**: 넓은 가설 탐색 폭($W$)과 깊은 점진적 정제($R$) 사이의 파레토 프론티어(Pareto Frontier)를 연산합니다.
- **결정론적 그리드 계획**: 검증된 리플레이 점수를 바탕으로 워커 예산과 탐침 한계를 자동으로 계획합니다.

---

## 빠른 시작

### 1. 에이전트 설정

DREAM-RSI는 표준 STDIO MCP 인터페이스를 통해 Claude Code, Antigravity, Cursor, OpenAI Codex와 연동됩니다.

#### Claude Code (`claude_desktop_config.json` 또는 프로젝트 MCP 설정)

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

#### Google Antigravity / Gemini CLI (`mcp_config.json`)

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

#### OpenAI Codex (`config.toml`)

```toml
[mcp_servers.dream-rsi]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"]
```

### 2. 터미널에서 직접 실행

`uv`를 통해 MCP 서버를 직접 실행할 수 있습니다:

```bash
uv run dream-rsi
```

모든 진단 로그는 표준 에러(stderr)로만 출력되어 STDIO 상의 JSON-RPC 프로토콜 무결성을 보장합니다.

---

## 작동 원리

1. **온라인 기록**: 에이전트가 문제를 탐색하면서 `dream_history_save_node` 도구로 각 시도 노드를 저장합니다. 실행 상태, 검증 결과, 오류 유형이 함께 보존됩니다.
2. **오프라인 리플레이 ("Dreaming")**: 세션이 유휴 상태이거나 종료된 후, `dream_replay_run`을 호출하여 가상 리플레이를 수행합니다. 외부 LLM 호출 없이 시뮬레이터가 과거 트리를 재현합니다.
3. **파레토 프론티어 산출**: `dream_replay_get_frontier`를 사용하여 다양한 $\beta$ 착취 파라미터에 걸친 최적 성능 곡선을 도출합니다.
4. **적응형 탐색 계획**: 에이전트는 `dream_policy_plan_grid`를 통해 다음 실제 문제 해결에 적합한 최적의 분기 폭($W$)과 정제 깊이($R$)를 추천받습니다.

---

## MCP 도구 목록

DREAM-RSI는 8개의 도구와 2개의 리소스를 제공합니다:

| 도구명 | 기능 | 주요 매개변수 | 반환값 |
| :--- | :--- | :--- | :--- |
| `dream_history_list` | 등록된 모든 탐색 트리 목록 및 세션 조회 | 없음 | 트리 ID 및 전체 개수 |
| `dream_history_get_tree` | 지정한 트리의 전체 위상 및 노드 정보 조회 | `tree_id` | 노드 계층 구조 및 메타데이터 |
| `dream_history_save_node` | 새로운 탐색 시도 노드 저장 | `tree_id`, `node_data` | 저장 상태 및 갱신된 노드 수 |
| `dream_replay_run` | 특정 트리에 대해 정책 오프라인 가상 리플레이 실행 | `tree_id`, `beta`, `worker_cap`, `max_budget` | 리플레이 점수 및 최대 성과 |
| `dream_replay_get_frontier` | 모든 트리를 대상으로 $\beta$ 스윕 파레토 프론티어 산출 | `beta_steps`, `worker_cap`, `max_budget` | 파레토 최적 포인트 목록 |
| `dream_policy_compare` | 후보 정책과 기준 정책의 성능 비교 평가 | `candidate_beta`, `baseline_beta`, `worker_cap` | 승률, 점수 변화량($\Delta$), 평가 |
| `dream_policy_plan_grid` | 다음 탐색 에피소드를 위한 분기 폭 $W$ 및 깊이 $R$ 계획 | `context` (선택) | 권장 $W$ 및 $R$ 값 |
| `dream_status` | 엔진 상태 및 스토리지 경로 무결성 확인 | 없음 | 정상 동작 여부 및 통계 |

### MCP 리소스

- `dream://history/manifest`: 저장된 모든 탐색 트리의 요약 매니페스트를 반환합니다.
- `dream://status`: 엔진 진단 정보 및 등록된 트리 수를 반환합니다.

---

## 수학적 정식화

### 탐색 vs. 활용 균형 ($\beta$)

동적 포트폴리오 정책은 후보 노드의 품질 점수와 활용 파라미터 $\beta \in [0, 1]$에 따라 후속 정제 대상을 선택합니다:

$$P(\text{refine} \mid \text{node}_i) \propto \exp\left(\frac{\beta \cdot \text{score}_i}{\tau}\right)$$

- $\beta \to 0$: 미검증된 다양한 가설을 폭넓게 탐색합니다.
- $\beta \to 1$: 높은 점수를 기록한 유망 노드를 집중적으로 파고듭니다.

### 그리드 최적화 $(W, R)$

가용 워커 예산 $B$ 내에서 분기 폭 $W$와 정제 깊이 $R$을 계획합니다:

$$W \cdot R \le B, \quad \max_{W, R} \mathbb{E}\left[\max_{i \le W} S_i^{(R)}\right]$$

---

## 개발 및 검증

DREAM-RSI는 Python 3.10 이상 및 `uv`를 사용합니다.

```bash
# 의존성 설치 및 동기화
uv sync

# 단위 및 통합 테스트 실행 (23개 테스트 통과)
uv run pytest

# Pyright 엄격 모드 정적 타입 분석
uv run pyright

# 라이브 STDIO MCP 프로토콜 검증 (8개 도구 전체 호출)
uv run python scripts/verify_mcp.py
```

---

## 라이선스 및 인용

MIT 라이선스에 따라 배포됩니다. 자세한 내용은 [LICENSE](../../LICENSE) 및 [NOTICE](../../NOTICE)를 참조하십시오.
논문 인용:

```bibtex
@article{zheng2026dreamrsi,
  title={Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems},
  author={Zheng, Kid and collaborators},
  journal={arXiv preprint arXiv:2609.14858},
  year={2026}
}
```
