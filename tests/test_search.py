from fastapi.testclient import TestClient
from sqlmodel import Session

from html_tool_manager.models import Tool


def test_search_by_name_prefix(session: Session, client: TestClient):
    # 1. Create test data
    tool1 = Tool(name="json formatter", description="Formats JSON.", filepath="t1.html", tags=["json", "formatter"])
    tool2 = Tool(name="jwt decoder", description="Decodes JWT.", filepath="t2.html", tags=["jwt", "decoder"])
    tool3 = Tool(name="text counter", description="Counts text characters.", filepath="t3.html", tags=["text", "counter"])

    session.add(tool1)
    session.add(tool2)
    session.add(tool3)
    session.commit()

    # DEBUG: Check if data exists in FTS table
    from sqlmodel import text
    fts_content = session.exec(text("SELECT rowid, name, description FROM tool_fts")).all()
    print(f"FTS table content ({len(fts_content)} rows):", fts_content)
    assert len(fts_content) == 3, "FTS table should be populated by the trigger"

    # 2. Perform search
    response = client.get("/api/tools/?q=name:j")
    assert response.status_code == 200
    data = response.json()

    # 3. Assert results
    assert len(data) == 2, "Should find 2 tools starting with 'j'"

    found_names = {item['name'] for item in data}
    assert "json formatter" in found_names
    assert "jwt decoder" in found_names
    assert "text counter" not in found_names

def test_search_by_tag(session: Session, client: TestClient):
    # 1. Create test data
    tool1 = Tool(name="json formatter", description="Formats JSON.", filepath="t1.html", tags=["json", "formatter", "util"])
    tool2 = Tool(name="jwt decoder", description="Decodes JWT.", filepath="t2.html", tags=["jwt", "decoder"])
    tool3 = Tool(name="text counter", description="Counts text characters.", filepath="t3.html", tags=["text", "counter", "util"])

    session.add(tool1)
    session.add(tool2)
    session.add(tool3)
    session.commit()

    # 2. Perform search for partial tag match
    response = client.get("/api/tools/?q=tag:ut")
    assert response.status_code == 200
    data = response.json()

    # 3. Assert results
    assert len(data) == 2, "Should find 2 tools with tags containing 'ut'"
    found_names = {item['name'] for item in data}
    assert "json formatter" in found_names
    assert "text counter" in found_names

def test_search_with_phrase(session: Session, client: TestClient):
    # 1. Create test data
    tool1 = Tool(name="My Awesome Tool", description="Something awesome.", filepath="t1.html", tags=[])
    tool2 = Tool(name="My Other Tool", description="Something else.", filepath="t2.html", tags=[])

    session.add(tool1)
    session.add(tool2)
    session.commit()

    # 2. Perform search
    response = client.get('/api/tools/?q=name:"Awesome Tool"')
    assert response.status_code == 200
    data = response.json()

    # 3. Assert results
    assert len(data) == 1
    assert data[0]['name'] == "My Awesome Tool"
