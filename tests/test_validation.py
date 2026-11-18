"""輸入驗證規則與邊界值（spec 5、第 8 節 #6–#12）。"""
import json

import pytest

from helpers import VALID_BODY, assert_validation, make_body, total

JSON_HDR = {"Content-Type": "application/json"}


def post_and_expect_422(client, payload, field=None):
    before = total(client)
    r = client.post("/objects", json=payload)
    assert_validation(r, field)
    assert total(client) == before  # 驗證失敗不得寫入


# ---------------- name ----------------
def test_name_missing(client):
    b = make_body()
    del b["name"]
    post_and_expect_422(client, b, "name")


@pytest.mark.parametrize("value", ["", "   ", "\t\n", "a" * 101, " " + "a" * 101 + " "])
def test_name_invalid_empty_or_too_long(client, value):
    post_and_expect_422(client, make_body(name=value), "name")


@pytest.mark.parametrize("value", [123, 1.5, True, ["a"], {"a": 1}, None])
def test_name_non_string(client, value):
    post_and_expect_422(client, make_body(name=value), "name")


@pytest.mark.parametrize("value", ["a\u0000b", "a\nb", "a\u001fb", "a\u007fb", "a\tb"])
def test_name_control_chars(client, value):
    post_and_expect_422(client, make_body(name=value), "name")


@pytest.mark.parametrize(
    "value,expected",
    [
        ("a" * 100, "a" * 100),
        ("中" * 100, "中" * 100),
        ("  ab  ", "ab"),
        (" " + "a" * 100 + " ", "a" * 100),
        ("x", "x"),
    ],
)
def test_name_valid_boundaries_and_strip(client, value, expected):
    r = client.post("/objects", json=make_body(name=value))
    assert r.status_code == 201, r.text
    assert r.json()["name"] == expected
    assert client.get(f"/objects/{r.json()['id']}").json()["name"] == expected


def test_name_chinese_101_rejected(client):
    post_and_expect_422(client, make_body(name="中" * 101), "name")


# ---------------- model_url ----------------
@pytest.mark.parametrize(
    "url",
    [
        "https://cdn.example.com/models/chair.glb",
        "http://localhost:8000/a.gltf",
        "HTTPS://EXAMPLE.COM/A.GLB",
        "https://example.com",
        "https://example.com/model",
        "http://a.com:65535/x",
        "http://a.com:1/x",
    ],
)
def test_model_url_valid_returned_verbatim(client, url):
    r = client.post("/objects", json=make_body(model_url=url))
    assert r.status_code == 201, r.text
    assert r.json()["model_url"] == url


@pytest.mark.parametrize(
    "url",
    [
        "example.com/a.glb",
        "ftp://example.com/a.glb",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/plain,hi",
        "https://exa mple.com/a.glb",
        "https://example.com/a\tb.glb",
        "https://example.com/a\nb.glb",
        " https://example.com/a.glb",
        "https://example.com/a.glb ",
        "",
        "http://",
        "http:///a.glb",
        "https://:80",
        "http://a.com:99999/x",
        "http://a.com:0/x",
    ],
)
def test_model_url_invalid(client, url):
    post_and_expect_422(client, make_body(model_url=url), "model_url")


@pytest.mark.parametrize("value", [123, True, None, ["https://a.com"], {"u": 1}])
def test_model_url_non_string(client, value):
    post_and_expect_422(client, make_body(model_url=value), "model_url")


def test_model_url_missing(client):
    b = make_body()
    del b["model_url"]
    post_and_expect_422(client, b, "model_url")


def _url_of_len(n):
    prefix = "https://example.com/"
    return prefix + "a" * (n - len(prefix))


def test_model_url_length_2048_ok(client):
    url = _url_of_len(2048)
    assert len(url) == 2048
    r = client.post("/objects", json=make_body(model_url=url))
    assert r.status_code == 201, r.text
    assert r.json()["model_url"] == url


def test_model_url_length_2049_rejected(client):
    url = _url_of_len(2049)
    assert len(url) == 2049
    post_and_expect_422(client, make_body(model_url=url), "model_url")


# ---------------- Vector3 ----------------
VEC_FIELDS = ["position", "rotation", "scale"]


@pytest.mark.parametrize("field", VEC_FIELDS)
def test_vector_missing_field(client, field):
    b = make_body()
    del b[field]
    post_and_expect_422(client, b, field)


@pytest.mark.parametrize("field", VEC_FIELDS)
@pytest.mark.parametrize(
    "vec",
    [
        {"x": 1, "y": 1},  # 缺分量
        {"x": 1, "y": 1, "z": 1, "w": 4},  # 多分量
        {"x": "1.5", "y": 1, "z": 1},  # 字串
        {"x": True, "y": 1, "z": 1},  # 布林
        {"x": None, "y": 1, "z": 1},  # null 分量
        [1, 1, 1],  # 陣列
        None,  # 整個向量 null
        "1,1,1",
    ],
    ids=["missing_z", "extra_w", "string", "bool", "null_comp", "array", "null_vec", "str_vec"],
)
def test_vector_invalid_shapes(client, field, vec):
    post_and_expect_422(client, make_body(**{field: vec}), field)


@pytest.mark.parametrize("field", VEC_FIELDS)
@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity", "1e400"])
def test_vector_non_finite_raw_json(client, field, token):
    b = make_body()
    b[field] = {"x": "__TOKEN__", "y": 1, "z": 1}
    raw = json.dumps(b).replace('"__TOKEN__"', token)
    before = total(client)
    r = client.post("/objects", content=raw, headers=JSON_HDR)
    assert_validation(r, field)
    assert total(client) == before


# ---------------- 範圍邊界 ----------------
@pytest.mark.parametrize(
    "field,value",
    [
        ("position", 1000000),
        ("position", -1000000),
        ("position", 0),
        ("rotation", 360),
        ("rotation", -360),
        ("rotation", 0),
        ("rotation", 359.9),
        ("scale", 0.0001),
        ("scale", 1),
        ("scale", 10000),
    ],
)
def test_range_valid(client, field, value):
    vec = {"x": value, "y": value, "z": value}
    r = client.post("/objects", json=make_body(**{field: vec}))
    assert r.status_code == 201, r.text
    assert r.json()[field] == {"x": float(value), "y": float(value), "z": float(value)}


@pytest.mark.parametrize(
    "field,value",
    [
        ("position", 1000000.001),
        ("position", -1000000.001),
        ("rotation", 360.0001),
        ("rotation", -360.0001),
        ("rotation", 720),
        ("scale", 0),
        ("scale", -0.0),
        ("scale", -1),
        ("scale", 10000.0001),
    ],
)
@pytest.mark.parametrize("comp", ["x", "y", "z"])
def test_range_invalid(client, field, value, comp):
    vec = {"x": 1, "y": 1, "z": 1}
    vec[comp] = value
    post_and_expect_422(client, make_body(**{field: vec}), field)


def test_rotation_not_normalized(client):
    r = client.post("/objects", json=make_body(rotation={"x": 360, "y": -360, "z": 0}))
    assert r.status_code == 201
    assert r.json()["rotation"] == {"x": 360.0, "y": -360.0, "z": 0.0}


# ---------------- 額外欄位 ----------------
@pytest.mark.parametrize(
    "extra",
    [
        {"foo": 1},
        {"id": "3f2b8c1e-9a4d-4e7b-8c21-5d6f7a8b9c0d"},
        {"created_at": "2026-11-18T08:30:00Z"},
        {"updated_at": "2026-11-18T08:30:00Z"},
    ],
)
def test_extra_top_level_fields(client, extra):
    b = make_body()
    b.update(extra)
    post_and_expect_422(client, b, next(iter(extra)))


def test_extra_fields_on_put(client, created):
    b = make_body()
    b["foo"] = 1
    assert_validation(client.put(f"/objects/{created['id']}", json=b), "foo")
    assert client.get(f"/objects/{created['id']}").json() == created


# ---------------- body 格式 ----------------
@pytest.mark.parametrize("raw", ["[]", '"abc"', "123", "null", "{bad json", '{"name": "a",}'])
def test_body_not_object_or_bad_json(client, raw):
    before = total(client)
    r = client.post("/objects", content=raw, headers=JSON_HDR)
    assert_validation(r)
    assert total(client) == before


@pytest.mark.parametrize("raw", [b"\xff\xfe", b'{"name": "\xff\xfe"}', b"\xc3\x28"])
def test_post_invalid_utf8_body(client, raw):
    """spec 1/4：編碼為 UTF-8；非法 UTF-8 body 屬 body 驗證失敗 → 422 VALIDATION_ERROR（不可 500）。"""
    before = total(client)
    r = client.post("/objects", content=raw, headers=JSON_HDR)
    assert_validation(r)
    assert total(client) == before


def test_put_invalid_utf8_body_does_not_modify(client, created):
    r = client.put(f"/objects/{created['id']}", content=b"\xff\xfe", headers=JSON_HDR)
    assert_validation(r)
    assert client.get(f"/objects/{created['id']}").json() == created


def test_post_missing_body(client):
    assert_validation(client.post("/objects"))


def test_put_missing_body(client, created):
    assert_validation(client.put(f"/objects/{created['id']}"))
    assert client.get(f"/objects/{created['id']}").json() == created


def test_put_bad_json_does_not_modify(client, created):
    r = client.put(f"/objects/{created['id']}", content="{bad", headers=JSON_HDR)
    assert_validation(r)
    assert client.get(f"/objects/{created['id']}").json() == created


def test_put_invalid_range_does_not_modify(client, created):
    r = client.put(
        f"/objects/{created['id']}", json=make_body(name="Changed", position={"x": 2e6, "y": 0, "z": 0})
    )
    assert_validation(r, "position")
    assert client.get(f"/objects/{created['id']}").json() == created


def test_error_details_have_no_ctx_or_input(client):
    raw = json.dumps(VALID_BODY).replace('"x": 1, "y": 0', '"x": NaN, "y": 0', 1)
    r = client.post("/objects", content=raw, headers=JSON_HDR)
    err = assert_validation(r, "position")
    for d in err["details"]:
        assert "ctx" not in d and "input" not in d
