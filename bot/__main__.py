import sys
from .config import ROOT, load_config
from .engine import run_once
from .hermes import create_review, send_to_hermes
from .sample_data import create
from .scheduler import run_scheduler

def main():
    cfg = load_config()
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    data_path = ROOT / cfg["data_file"]
    if command == "demo":
        create(str(data_path)); report = run_once(cfg); print(report)
    elif command == "run":
        print(run_once(cfg))
    elif command == "report":
        print(run_once(cfg))
    elif command == "hermes":
        review = create_review(str(ROOT / cfg["observations_file"]), str(ROOT / "data"))
        print(review)
        if cfg["hermes_url"]:
            print(send_to_hermes(review, cfg["hermes_url"], cfg["hermes_api_key"]))
    elif command == "schedule":
        run_scheduler()
    else:
        raise SystemExit(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
