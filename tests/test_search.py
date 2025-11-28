from fastapi.testclient import TestClient
from sqlmodel import Session


def test_search_by_name_prefix(session: Session, client: TestClient):
    # 1. Create test data via API
    tool1_data = {"name": "json formatter", "description": "Formats JSON.", "html_content": "<p>json</p>"}
    tool2_data = {"name": "jwt decoder", "description": "Decodes JWT.", "html_content": "<p>jwt</p>"}
    tool3_data = {"name": "text counter", "description": "Counts text characters.", "html_content": "<p>text</p>"}

    res1 = client.post("/api/tools/", json=tool1_data)
    res2 = client.post("/api/tools/", json=tool2_data)
    res3 = client.post("/api/tools/", json=tool3_data)

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res3.status_code == 201

    tool1_id = res1.json()["id"]
    tool2_id = res2.json()["id"]
    tool3_id = res3.json()["id"]

    # 2. Perform search
    response = client.get("/api/tools/?q=name:j")
    assert response.status_code == 200
    data = response.json()

    # 3. Assert results
    assert len(data) == 2, "Should find 2 tools starting with 'j'"

    found_names = {item["name"] for item in data}
    assert "json formatter" in found_names
    assert "jwt decoder" in found_names
    assert "text counter" not in found_names


def test_search_by_tag(session: Session, client: TestClient):
    # 1. Create test data via API
    tool1_data = {
        "name": "json formatter",
        "description": "Formats JSON.",
        "html_content": "<p>json</p>",
        "tags": ["json", "formatter", "util"],
    }
    tool2_data = {
        "name": "jwt decoder",
        "description": "Decodes JWT.",
        "html_content": "<p>jwt</p>",
        "tags": ["jwt", "decoder"],
    }
    tool3_data = {
        "name": "text counter",
        "description": "Counts text characters.",
        "html_content": "<p>text</p>",
        "tags": ["text", "counter", "util"],
    }

    res1 = client.post("/api/tools/", json=tool1_data)
    res2 = client.post("/api/tools/", json=tool2_data)
    res3 = client.post("/api/tools/", json=tool3_data)

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res3.status_code == 201

    # 2. Perform search for partial tag match
    response = client.get("/api/tools/?q=tag:ut")
    assert response.status_code == 200
    data = response.json()

    # 3. Assert results
    assert len(data) == 2, "Should find 2 tools with tags containing 'ut'"
    found_names = {item["name"] for item in data}
    assert "json formatter" in found_names
    assert "text counter" in found_names


def test_search_with_phrase(session: Session, client: TestClient):
    # 1. Create test data via API
    tool1_data = {"name": "My Awesome Tool", "description": "Something awesome.", "html_content": "<p>awesome</p>"}
    tool2_data = {"name": "My Other Tool", "description": "Something else.", "html_content": "<p>else</p>"}
    tool3_data = {"name": "Another Tool", "description": "This is an Awesome Tool.", "html_content": "<p>another</p>"}

    res1 = client.post("/api/tools/", json=tool1_data)
    res2 = client.post("/api/tools/", json=tool2_data)
    res3 = client.post("/api/tools/", json=tool3_data)

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res3.status_code == 201

    # 2. Perform search
    response = client.get('/api/tools/?q=name:"Awesome Tool"')
    assert response.status_code == 200
    data = response.json()

    # 3. Assert results
    assert len(data) == 1
    assert data[0]["name"] == "My Awesome Tool"
