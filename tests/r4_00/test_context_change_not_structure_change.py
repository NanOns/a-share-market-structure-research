from forward.observation import changed_fields
def test_context():assert changed_fields({"warning":"A"},{"warning":"B"})==[]
