# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for PixelGrid script operations."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.script import (
    center_pixel_matrix,
    detect_background_color,
    flatten_matrix_to_tuples,
    generate_pixel_art,
    save_pixel_matrix,
    upscale_matrix,
    validate_pixel_matrix,
)


@pytest.fixture
def sample_16x16_matrix() -> list[list[list[int]]]:
    """Returns a valid 16x16 RGB matrix."""
    return [[[255, 0, 128] for _ in range(16)] for _ in range(16)]


@pytest.fixture
def sample_8x8_matrix() -> list[list[list[int]]]:
    """Returns a valid 8x8 RGB matrix."""
    return [[[0, 0, 0] for _ in range(8)] for _ in range(8)]


def test_validate_pixel_matrix_valid(
    sample_16x16_matrix: list[list[list[int]]],
) -> None:
    """Verifies valid 16x16 matrix passes validation."""
    assert validate_pixel_matrix(sample_16x16_matrix, expected_size=16) is True


def test_validate_pixel_matrix_8x8_valid(
    sample_8x8_matrix: list[list[list[int]]],
) -> None:
    """Verifies valid 8x8 matrix passes validation."""
    assert validate_pixel_matrix(sample_8x8_matrix, expected_size=8) is True


def test_validate_pixel_matrix_invalid_dimensions() -> None:
    """Verifies matrix with wrong dimensions fails validation."""
    bad_matrix = [[[255, 0, 0]] * 7] * 8
    assert validate_pixel_matrix(bad_matrix) is False


def test_validate_pixel_matrix_invalid_values() -> None:
    """Verifies out-of-range RGB values fail validation."""
    bad_matrix = [[[300, -5, 0]] * 8] * 8
    assert validate_pixel_matrix(bad_matrix) is False


def test_flatten_matrix_to_tuples(
    sample_16x16_matrix: list[list[list[int]]],
) -> None:
    """Verifies 3D matrix flattens to 256 RGB tuples."""
    flat = flatten_matrix_to_tuples(sample_16x16_matrix)
    assert len(flat) == 256
    assert flat[0] == (255, 0, 128)
    assert isinstance(flat[0], tuple)


def test_save_pixel_matrix(
    tmp_path, sample_16x16_matrix: list[list[list[int]]]
) -> None:
    """Verifies matrix serialization to disk with timestamp."""
    ts = datetime(2026, 7, 7, 19, 0, 0)
    out_path = save_pixel_matrix(
        sample_16x16_matrix,
        str(tmp_path),
        "8-bit garden",
        timestamp=ts,
    )

    assert "8-bit_garden_2026-07-07_19-00-00.json" in out_path
    with open(out_path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == sample_16x16_matrix


def test_generate_pixel_art_success(
    sample_8x8_matrix: list[list[list[int]]],
) -> None:
    """Verifies successful 8x8 generation and 2x upscaling to 16x16."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(sample_8x8_matrix)
    mock_client.models.generate_content.return_value = mock_response

    result = generate_pixel_art(
        theme="super mario",
        project_id="leeboonstra",
        client=mock_client,
        grid_size=8,
    )
    assert len(result) == 16
    assert len(result[0]) == 16
    mock_client.models.generate_content.assert_called_once()


def test_upscale_matrix(sample_8x8_matrix: list[list[list[int]]]) -> None:
    """Verifies 8x8 matrix scales 2x into 16x16."""
    upscaled = upscale_matrix(sample_8x8_matrix, scale=2)
    assert len(upscaled) == 16
    assert len(upscaled[0]) == 16


def test_detect_background_color() -> None:
    """Verifies background color detection from corner pixel."""
    matrix = [[[10, 20, 30] for _ in range(8)] for _ in range(8)]
    assert detect_background_color(matrix) == [10, 20, 30]


def test_center_pixel_matrix() -> None:
    """Verifies off-center sprite is centered inside the matrix."""
    bg = [0, 0, 0]
    fg = [255, 255, 255]
    matrix = [[bg for _ in range(8)] for _ in range(8)]
    matrix[0][0] = fg  # Single pixel at top-left corner

    centered = center_pixel_matrix(matrix)
    assert centered[3][3] == fg
    assert centered[0][0] == bg


def test_ensure_bluetooth_ready() -> None:
    """Verifies ensure_bluetooth_ready executes cleanly without error."""
    from src.script import ensure_bluetooth_ready

    ensure_bluetooth_ready()
