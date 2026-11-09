import json
import urllib.request
from datetime import datetime
from pathlib import Path

def create_review(observation_file: str, output_dir: str = "data") -> Path:
    data = json.loads(Path(observation_file).read_text())
    date = datetime.now().strftime("%Y-%m-%d")
    review = {
        "created_at": datetime.now().isoformat(),
        "task": "Review observations date-wise and propose paper-trading improvements.",
        "approval_required": True,
        "instructions": [
            "Do not issue live orders.",
            "Do not change risk limits.",
            "Propose new strategy versions only after evidence-based analysis.",
            "Return a plan with evidence, tests, expected impact, and rollback criteria."
        ],
        "observations": data
    }
    path = Path(output_dir) / f"hermes_review_{date}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, indent=2, default=str))
    return path

def send_to_hermes(review_path: Path, url: str, api_key: str = ""):
    if not url:
        return False
    body = review_path.read_bytes()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as response:
        return 200 <= response.status < 300
