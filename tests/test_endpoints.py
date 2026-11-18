"""5 個端點的 CRUD 行為（spec 6、第 8 節 #1–#5、#13、#14）。"""
import time

import pytest

from helpers import DT_Z, MISSING_ID, UUID_V4_LOWER, assert_error, assert_validation, make_body

FIELDS = {"id", "name", "model_url", "position", "rotation", "scale", "created_at", "updated_at"}


# ---------------- POST ----------------
def test_post_valid_returns_201_full_object(client, body):
    r = client.post("/objects", json=body)
    assert r.status_code == 201
    data = r.json()
    assert set(data.keys()) == FIELDS
    assert UUID_V4_LOWER.match(data["id"])
    assert data["name"] == "Chair"
    assert data["model_url"] == body["model_url"]
    assert data["position"] == {"x": 1.0, "y": 0.0, "z": -2.5}
    assert data["rotation"] == {"x": 0.0, "y": 90.0, "z": 0.0}
    assert data["scale"] == {"x": 1.0, "y": 1.0, "z": 1.0}
    # 整數輸入回應為浮點數
    assert isinstance(data["position"]["x"], float)
    assert isinstance(data["scale"]["y"], float)
    assert DT_Z.match(data["created_at"])
    assert DT_Z.match(data["updated_at"])
    assert data["created_at"] == data["updated_at"]
    assert r.headers["location"] == f"/objects/{data['id']}"
    assert r.headers["content-type"].startswith("application/json")


def test_post_duplicate_name_allowed(client, body):
    assert client.post("/objects", json=body).status_code == 201
    assert client.post("/objects", json=body).status_code == 201
    assert client.get("/objects").json()["total"] == 2


# ---------------- GET list ----------------
def test_list_empty(client):
    r = client.get("/objects")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_list_with_data(client, created):
    r = client.get("/objects")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["limit"] == 50 and data["offset"] == 0
    assert data["items"] == [created]


def test_list_limit_offset_total_and_order(client):
    ids = []
    for i in range(5):
        r = client.post("/objects", json=make_body(name=f"obj{i}"))
        assert r.status_code == 201
        ids.append(r.json()["id"])
        time.sleep(0.002)
    all_items = client.get("/objects").json()["items"]
    # 排序：created_at 升冪，相同則 id 升冪
    keys = [(o["created_at"], o["id"]) for o in all_items]
    assert keys == sorted(keys)
    assert [o["id"] for o in all_items] == ids

    r = client.get("/objects", params={"limit": 2, "offset": 1})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert data["limit"] == 2 and data["offset"] == 1
    assert [o["id"] for o in data["items"]] == ids[1:3]


def test_list_offset_beyond_total(client, created):
    r = client.get("/objects", params={"offset": 10})
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 1


@pytest.mark.parametrize("limit", [1, 100])
def test_list_limit_boundaries_ok(client, limit):
    r = client.get("/objects", params={"limit": limit})
    assert r.status_code == 200
    assert r.json()["limit"] == limit


@pytest.mark.parametrize(
    "params,field",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"limit": "abc"}, "limit"),
        ({"limit": "1.5"}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": "abc"}, "offset"),
    ],
)
def test_list_invalid_query_422(client, params, field):
    r = client.get("/objects", params=params)
    err = assert_validation(r, field)
    assert any(d["loc"][0] == "query" for d in err["details"])


def test_list_unknown_query_ignored(client):
    r = client.get("/objects", params={"foo": "bar"})
    assert r.status_code == 200


# ---------------- GET single ----------------
def test_get_existing(client, created):
    r = client.get(f"/objects/{created['id']}")
    assert r.status_code == 200
    assert r.json() == created


def test_get_not_found(client):
    assert_error(client.get(f"/objects/{MISSING_ID}"), 404, "NOT_FOUND")


@pytest.mark.parametrize(
    "bad_id",
    ["abc", "123", "3f2b8c1e9a4d4e7b8c215d6f7a8b9c0d", "3f2b8c1e-9a4d-4e7b-8c21-5d6f7a8b9c0d0"],
)
def test_get_invalid_id_422(client, bad_id):
    err = assert_validation(client.get(f"/objects/{bad_id}"))
    assert any(d["loc"] == ["path", "id"] for d in err["details"]), err["details"]


def test_get_uppercase_uuid(client, created):
    r = client.get(f"/objects/{created['id'].upper()}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


# ---------------- PUT ----------------
def test_put_valid(client, created):
    time.sleep(0.002)
    new = make_body(
        name="Table",
        model_url="http://localhost:8000/a.gltf",
        position={"x": 5, "y": 6, "z": 7},
        rotation={"x": 360, "y": -360, "z": 0},
        scale={"x": 2, "y": 2, "z": 2},
    )
    r = client.put(f"/objects/{created['id']}", json=new)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == created["id"]
    assert data["created_at"] == created["created_at"]
    assert data["updated_at"] >= data["created_at"]
    assert data["name"] == "Table"
    assert data["model_url"] == "http://localhost:8000/a.gltf"
    assert data["position"] == {"x": 5.0, "y": 6.0, "z": 7.0}
    assert data["rotation"] == {"x": 360.0, "y": -360.0, "z": 0.0}
    assert data["scale"] == {"x": 2.0, "y": 2.0, "z": 2.0}
    # 持久化
    assert client.get(f"/objects/{created['id']}").json() == data


def test_put_not_found_does_not_create(client, body):
    assert_error(client.put(f"/objects/{MISSING_ID}", json=body), 404, "NOT_FOUND")
    assert client.get("/objects").json()["total"] == 0


def test_put_invalid_body_does_not_modify(client, created):
    r = client.put(f"/objects/{created['id']}", json=make_body(name=""))
    assert_validation(r, "name")
    assert client.get(f"/objects/{created['id']}").json() == created


def test_put_partial_body_422(client, created):
    r = client.put(f"/objects/{created['id']}", json={"name": "Only"})
    assert_validation(r)
    assert client.get(f"/objects/{created['id']}").json() == created


def test_put_invalid_id_422(client, body):
    err = assert_validation(client.put("/objects/abc", json=body))
    assert any(d["loc"] == ["path", "id"] for d in err["details"])


def test_put_422_before_404(client):
    r = client.put(f"/objects/{MISSING_ID}", json=make_body(scale={"x": 0, "y": 1, "z": 1}))
    assert_validation(r, "scale")


def test_put_uppercase_uuid(client, created, body):
    r = client.put(f"/objects/{created['id'].upper()}", json=make_body(name="Up"))
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


# ---------------- DELETE ----------------
def test_delete_flow(client, created):
    oid = created["id"]
    r = client.delete(f"/objects/{oid}")
    assert r.status_code == 204
    assert r.content == b""
    assert_error(client.delete(f"/objects/{oid}"), 404, "NOT_FOUND")
    assert_error(client.get(f"/objects/{oid}"), 404, "NOT_FOUND")
    assert client.get("/objects").json()["total"] == 0


def test_delete_not_found(client):
    assert_error(client.delete(f"/objects/{MISSING_ID}"), 404, "NOT_FOUND")


def test_delete_invalid_id_422(client):
    err = assert_validation(client.delete("/objects/123"))
    assert any(d["loc"] == ["path", "id"] for d in err["details"])


def test_delete_uppercase_uuid(client, created):
    assert client.delete(f"/objects/{created['id'].upper()}").status_code == 204
    assert client.get(f"/objects/{created['id']}").status_code == 404


# ---------------- 405 / 404 route ----------------
def test_patch_405(client, created):
    assert_error(client.patch(f"/objects/{created['id']}", json={"name": "x"}), 405, "METHOD_NOT_ALLOWED")


def test_delete_collection_405(client):
    assert_error(client.delete("/objects"), 405, "METHOD_NOT_ALLOWED")


def test_unknown_route_404(client):
    assert_error(client.get("/nope"), 404, "NOT_FOUND")


@pytest.mark.parametrize("method", ["get", "post"])
def test_trailing_slash_collection_404_not_redirect(client, method):
    """spec 4：路由不存在 → 404 NOT_FOUND 統一格式，不得 307 轉址到 /objects。"""
    r = getattr(client, method)("/objects/", follow_redirects=False)
    assert r.status_code != 307, r.headers
    assert "location" not in {k.lower() for k in r.headers.keys()}
    assert_error(r, 404, "NOT_FOUND")


def test_trailing_slash_item_404_not_redirect(client, created):
    r = client.get(f"/objects/{created['id']}/", follow_redirects=False)
    assert r.status_code != 307, r.headers
    assert_error(r, 404, "NOT_FOUND")


def test_isolation_db_is_fresh(client):
    """每個測試都應從空資料庫開始。"""
    assert client.get("/objects").json()["total"] == 0
