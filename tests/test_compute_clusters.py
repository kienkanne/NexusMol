import numpy as np

from nexus.dock.utils._compute_clusters import calculate_cluster_metrics, _sanitize_distance_matrix


def test_sanitize_distance_matrix_symmetrizes_and_fills_nan():
    matrix = np.array([
        [0.0, 1.5, np.nan],
        [2.0, 0.0, 3.0],
        [np.nan, 3.1, 0.0],
    ])

    sanitized = _sanitize_distance_matrix(matrix, threshold=2.0)

    assert sanitized.shape == (3, 3)
    assert np.allclose(sanitized[0, 1], sanitized[1, 0])
    assert np.allclose(sanitized[0, 2], sanitized[2, 0])
    assert sanitized[0, 0] == 0.0
    assert not np.isnan(sanitized).any()
    assert sanitized[0, 2] > 0.0


def test_calculate_cluster_metrics_handles_nan_and_singleton():
    matrix = np.array([
        [0.0, 1.5, np.nan],
        [1.5, 0.0, 2.5],
        [np.nan, 2.5, 0.0],
    ])

    clusters = calculate_cluster_metrics(matrix, threshold=2.0)

    assert isinstance(clusters, dict)
    assert all("representative_idx" in value for value in clusters.values())
    assert all("pose_indices" in value for value in clusters.values())
    assert sum(len(value["pose_indices"]) for value in clusters.values()) == 3
