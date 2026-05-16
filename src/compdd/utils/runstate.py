import json
from pathlib import Path


class State:
    """
    Simple checkpoint state for resume support.
    """

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.exists():
            self.state = self.load()
        else:
            self.state = {}

    def load(self):
        with open(self.path) as f:
            return json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.state, f, indent=2)

    def mark_running(self, stage):
        self.state[stage] = "running"
        self.save()

    def mark_failed(self, stage):
        self.state[stage] = "failed"
        self.save()

    def mark_done(self, stage: str, output=None):
        # Recursively convert Path objects to strings, but keep list structures intact
        def serialize(obj):
            if isinstance(obj, (list, tuple)):
                return [serialize(i) for i in obj]
            if isinstance(obj, Path):
                return str(obj)
            return obj

        self.state[stage] = {"status": "done", "output": serialize(output)}
        self.save()

    def get_output(self, stage: str):
        entry = self.state.get(stage, {})
        if not isinstance(entry, dict):
            return None
            
        val = entry.get("output")
        
        # If it's a list, return it (the caller will unpack the tuple of lists)
        if isinstance(val, list):
            return val
            
        # If it's a single string, it might be a path
        return Path(val) if val else None
    
    def is_done(self, stage: str) -> bool:
        entry = self.state.get(stage, {})
        return (entry.get("status") == "done") if isinstance(entry, dict) else (entry == "done")
