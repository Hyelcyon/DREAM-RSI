from __future__ import annotations

import pytest

from dream_rsi.core.models import Observation, TreeNode
from dream_rsi.core.signals import (
    BranchTrajectory,
    branch_failed_hard,
    branch_promising,
    probe_improved_vs_baseline,
    probe_improved_vs_parent,
)


def test_observation_signal_helpers() -> None:
    obs_ok = Observation(
        branch=1,
        attempt=1,
        score=0.8,
        evaluated=True,
        valid=True,
        fail_class="ok",
        delta_vs_baseline=0.2,
        delta_vs_parent=0.1,
    )
    assert obs_ok.is_successful is True
    assert branch_promising(obs_ok) is True
    assert branch_failed_hard(obs_ok) is False
    assert probe_improved_vs_parent(obs_ok) is True
    assert probe_improved_vs_baseline(obs_ok) is True

    obs_hard = Observation(
        branch=1,
        attempt=2,
        score=0.8,
        evaluated=True,
        valid=False,
        fail_class="environment_failure",
        error="Driver error",
    )
    assert obs_hard.is_successful is False
    assert branch_failed_hard(obs_hard) is True
    assert branch_promising(obs_hard) is False

    obs_repairable = Observation(
        branch=1,
        attempt=3,
        score=0.8,
        evaluated=True,
        valid=False,
        fail_class="shape_mismatch",
        error="Dimension mismatch",
    )
    assert obs_repairable.is_successful is False
    assert obs_repairable.is_repairable is True
    assert branch_failed_hard(obs_repairable) is False


def test_branch_trajectory_tracking() -> None:
    traj = BranchTrajectory(branch_id=1)

    node1 = TreeNode(
        node_id="n1",
        branch_id=1,
        attempt_index=1,
        depth=1,
        observation=Observation(
            branch=1, attempt=1, score=0.6, evaluated=True, valid=True, fail_class="ok"
        ),
    )
    traj.add_node(node1)
    assert traj.has_successful_anchor is True
    assert traj.successful_anchor_score == 0.6
    assert traj.consecutive_failures == 0

    node2 = TreeNode(
        node_id="n2",
        parent_id="n1",
        branch_id=1,
        attempt_index=2,
        depth=2,
        observation=Observation(
            branch=1, attempt=2, score=0.6, evaluated=True, valid=False, fail_class="shape_mismatch"
        ),
    )
    traj.add_node(node2)
    assert traj.consecutive_failures == 1
    assert traj.successful_anchor_score == 0.6

    node3 = TreeNode(
        node_id="n3",
        parent_id="n2",
        branch_id=1,
        attempt_index=3,
        depth=3,
        observation=Observation(
            branch=1, attempt=3, score=0.9, evaluated=True, valid=True, fail_class="ok"
        ),
    )
    traj.add_node(node3)
    assert traj.consecutive_failures == 0
    assert traj.successful_anchor_score == 0.9
    assert traj.score_trend == pytest.approx(0.3)
