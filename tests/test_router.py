# Tests for ai-router
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ai_router import DEFAULT_CONFIG, ModelRouter
from types import SimpleNamespace

def test_init():
    r = ModelRouter()
    assert len(r.providers) > 0
    print("✓ Init OK")

def test_alias():
    r = ModelRouter()
    assert r.resolve_model("gpt-4o-mini") == "deepseek-chat"
    assert r.resolve_model("unknown") == "unknown"
    print("✓ Alias OK")

def test_find():
    r = ModelRouter()
    ps = r.find_providers("deepseek-chat")
    assert len(ps) > 0
    assert ps[0].name == "deepseek"
    print("✓ Find OK")

def test_error():
    r = ModelRouter()
    req = SimpleNamespace(model="nonexistent", messages=[], stream=False, temperature=1.0, max_tokens=4096)
    resp = r.chat_completion(req)
    assert "error" in resp["choices"][0]["message"]["content"]
    print("✓ Error OK")

if __name__ == "__main__":
    test_init(); test_alias(); test_find(); test_error()
    print("\nAll tests passed!") 
