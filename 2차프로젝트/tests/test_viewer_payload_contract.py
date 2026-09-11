"""Unity 뷰어 전송 계약 검증.

`/api/viewer/schedule/{algorithm}` 응답이 unity-viewer 의 전송 계약
(`unity-viewer/Assets/StreamingAssets/mock_schedule.schema.md`) 을 만족하는지
확인한다. 검증 규칙은 C# 매퍼(`SchedulePayloadMapper.cs`) 가 강제하는 항목을
그대로 미러링한 것이다. Unity 에디터 없이 계약 위반을 잡기 위한 안전망이다.

실행: pytest tests/test_viewer_payload_contract.py
"""

import os
import re
import sys
from datetime import datetime

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.main import get_viewer_schedule, schedules_cache  # noqa: E402

# C# 매퍼의 OffsetSuffix 정규식과 같은 규칙: 끝에 Z 또는 +09:00 형태가 있어야 한다.
OFFSET_SUFFIX = re.compile(r"(Z|[+-]\d{2}:\d{2})$")

ALLOWED_STATUS = {"waiting", "in_progress", "completed"}
ALLOWED_BLOCK_TYPE = {"FLAT", "CURVED"}
ALLOWED_ACCEPTS = {"FLAT", "CURVED", "ANY"}

ALGORITHMS = sorted(schedules_cache.keys())


def parse_offset_time(text, ctx, errors):
    """오프셋이 명시된 ISO-8601 인지 확인하고 파싱한다."""
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{ctx}: 시각 문자열이 비어 있습니다.")
        return None
    if not OFFSET_SUFFIX.search(text):
        errors.append(f"{ctx}: '{text}' 에 UTC 오프셋이 없습니다.")
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{ctx}: '{text}' 를 ISO-8601 로 파싱할 수 없습니다.")
        return None


def check_size(entity, ctx, errors):
    for field in ("length", "width", "height"):
        value = entity.get(field)
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"{ctx}: {field} 가 0 보다 커야 합니다 (받은 값 {value!r}).")


def check_position(position, ctx, errors):
    if not isinstance(position, list) or len(position) != 3:
        errors.append(f"{ctx}: position 은 길이 3 배열이어야 합니다 (받은 값 {position!r}).")
        return
    for axis, value in zip("xyz", position):
        if not isinstance(value, (int, float)) or value != value or abs(value) == float("inf"):
            errors.append(f"{ctx}: position.{axis} 가 유한값이 아닙니다 ({value!r}).")


def validate(payload):
    """매퍼와 동일한 방식으로 모든 위반을 누적해 반환한다."""
    errors = []

    major = str(payload.get("schema_version", "")).split(".")[0]
    if major != "1":
        errors.append(f"schema_version '{payload.get('schema_version')}' 의 메이저가 1 이 아닙니다.")

    if payload.get("project_epoch"):
        parse_offset_time(payload["project_epoch"], "payload.project_epoch", errors)

    platens = payload.get("platens") or []
    blocks = payload.get("blocks") or []
    if not platens:
        errors.append("platens 배열이 비어 있습니다.")
    if not blocks:
        errors.append("blocks 배열이 비어 있습니다.")

    platen_ids = set()
    platen_size = {}
    for i, platen in enumerate(platens):
        pid = platen.get("platen_id")
        ctx = f"platens[{i}]"
        if not isinstance(pid, str) or not pid.strip():
            errors.append(f"{ctx}: platen_id 가 비어 있습니다.")
            continue
        ctx = f"platen '{pid}'"
        if pid in platen_ids:
            errors.append(f"{ctx}: platen_id 가 중복됩니다.")
            continue
        platen_ids.add(pid)
        check_size(platen, ctx, errors)
        platen_size[pid] = (platen.get("length"), platen.get("width"))
        if "position" in platen:
            check_position(platen["position"], f"{ctx}.position", errors)
        accepts = platen.get("accepts_block_type", "ANY")
        if accepts not in ALLOWED_ACCEPTS:
            errors.append(f"{ctx}: accepts_block_type '{accepts}' 는 허용되지 않습니다.")

    block_ids = set()
    for i, block in enumerate(blocks):
        bid = block.get("block_id")
        ctx = f"blocks[{i}]"
        if not isinstance(bid, str) or not bid.strip():
            errors.append(f"{ctx}: block_id 가 비어 있습니다.")
            continue
        ctx = f"block '{bid}'"
        if bid in block_ids:
            errors.append(f"{ctx}: block_id 가 중복됩니다.")
            continue
        block_ids.add(bid)

        platform_id = block.get("platform_id")
        if not platform_id:
            errors.append(f"{ctx}: platform_id 가 비어 있습니다.")
        elif platform_id not in platen_ids:
            errors.append(f"{ctx}: platform_id '{platform_id}' 에 해당하는 정반이 없습니다.")

        if block.get("status") not in ALLOWED_STATUS:
            errors.append(f"{ctx}: status '{block.get('status')}' 는 허용되지 않습니다.")
        if block.get("block_type") not in ALLOWED_BLOCK_TYPE:
            errors.append(f"{ctx}: block_type '{block.get('block_type')}' 는 허용되지 않습니다.")

        check_size(block, ctx, errors)
        check_position(block.get("position"), f"{ctx}.position", errors)

        start = parse_offset_time(block.get("start_time"), f"{ctx}.start_time", errors)
        end = parse_offset_time(block.get("end_time"), f"{ctx}.end_time", errors)
        if block.get("due_time"):
            parse_offset_time(block["due_time"], f"{ctx}.due_time", errors)
        if start and end and start >= end:
            errors.append(f"{ctx}: start_time 이 end_time 보다 빠르지 않습니다.")

    return errors


def check_blocks_inside_platens(payload):
    """계약이 강제하지는 않지만 화면이 깨지는 조건: 블록 발자국이 판 밖으로 나감."""
    size = {p["platen_id"]: (p["length"], p["width"]) for p in payload["platens"]}
    outside = []
    for block in payload["blocks"]:
        pl, pw = size[block["platform_id"]]
        x, _, z = block["position"]
        if x < 0 or z < 0 or x + block["length"] > pl + 1e-6 or z + block["width"] > pw + 1e-6:
            outside.append(block["block_id"])
    return outside


def check_no_overlap_per_platen(payload):
    """정반당 동시 1블록 제약. 실스케줄이 이를 지키는지 확인한다."""
    by_platen = {}
    for block in payload["blocks"]:
        by_platen.setdefault(block["platform_id"], []).append(
            (block["start_time"], block["end_time"], block["block_id"])
        )
    overlaps = []
    for pid, spans in by_platen.items():
        spans.sort()
        for i in range(len(spans) - 1):
            if spans[i][1] > spans[i + 1][0]:
                overlaps.append((pid, spans[i][2], spans[i + 1][2]))
    return overlaps


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_payload_satisfies_unity_contract(algorithm):
    payload = get_viewer_schedule(algorithm)
    errors = validate(payload)
    assert not errors, f"{algorithm}: 계약 위반 {len(errors)}건\n" + "\n".join(errors[:20])


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_every_block_stays_inside_its_platen(algorithm):
    payload = get_viewer_schedule(algorithm)
    outside = check_blocks_inside_platens(payload)
    assert not outside, f"{algorithm}: 판 밖으로 나간 블록 {len(outside)}건 - {outside[:5]}"


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_one_block_per_platen_at_a_time(algorithm):
    payload = get_viewer_schedule(algorithm)
    overlaps = check_no_overlap_per_platen(payload)
    assert not overlaps, f"{algorithm}: 같은 정반에서 기간이 겹치는 쌍 {len(overlaps)}건 - {overlaps[:3]}"


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_scale_matches_real_data(algorithm):
    payload = get_viewer_schedule(algorithm)
    assert len(payload["platens"]) == 66
    assert len(payload["blocks"]) == 872
    assert payload["adapter_notes"]["skipped_missing_block_spec"] == 0
    assert payload["adapter_notes"]["skipped_unknown_platen"] == 0


def test_existing_endpoints_still_serialize():
    """실데이터의 결측값(height_limit_m 의 '9M', 문자열 컬럼의 NaN) 때문에
    /api/platens 가 500 을 내던 것을 관용 파서로 고쳤다. 회귀 방지용."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    for path in ["/health", "/api/platens", "/api/leaderboard", "/api/schedule/ortools"]:
        assert client.get(path).status_code == 200, f"{path} 가 200 이 아닙니다."


@pytest.mark.parametrize("algorithm", ALGORITHMS)
def test_viewer_endpoint_serializes_over_http(algorithm):
    """NaN 이 섞이면 FastAPI 의 JSON 직렬화가 실패한다. 함수 직접 호출로는
    안 잡히므로 HTTP 응답으로 확인한다."""
    from fastapi.testclient import TestClient
    from app.main import app

    response = TestClient(app).get(f"/api/viewer/schedule/{algorithm}")
    assert response.status_code == 200
    assert len(response.json()["blocks"]) == 872


def test_unknown_algorithm_returns_404():
    from fastapi.testclient import TestClient
    from app.main import app

    assert TestClient(app).get("/api/viewer/schedule/nope").status_code == 404
