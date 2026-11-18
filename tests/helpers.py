import copy
import re

UUID_V4_LOWER = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
DT_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
MISSING_ID = "00000000-0000-4000-8000-000000000000"

VALID_BODY = {
    "name": "Chair",
    "model_url": "https://cdn.example.com/models/chair.glb",
    "position": {"x": 1, "y": 0, "z": -2.5},
    "rotation": {"x": 0, "y": 90, "z": 0},
    "scale": {"x": 1, "y": 1, "z": 1},
}


def make_body(**overrides):
    b = copy.deepcopy(VALID_BODY)
    for k, v in overrides.items():
        b[k] = v
    return b


def assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    data = resp.json()
    assert set(data.keys()) == {"error"}, data
    err = data["error"]
    assert err["code"] == code
    assert isinstance(err["message"], str) and err["message"]
    assert isinstance(err["details"], list)
    if status == 422:
        assert len(err["details"]) > 0
        for d in err["details"]:
            assert set(d.keys()) == {"loc", "msg", "type"}
            assert d["loc"][0] in ("body", "path", "query")
    else:
        assert err["details"] == []
    return err


def assert_validation(resp, field=None):
    err = assert_error(resp, 422, "VALIDATION_ERROR")
    if field is not None:
        assert any(field in d["loc"] for d in err["details"]), err["details"]
    return err


def total(client):
    r = client.get("/objects")
    assert r.status_code == 200
    return r.json()["total"]
