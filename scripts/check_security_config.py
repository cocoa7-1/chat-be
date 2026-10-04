"""Read settings privately and report booleans only; never import app/DB/AI."""
import argparse
import json
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Existing Linux service PID, to reuse its cwd and process environment")
    args = parser.parse_args()
    try:
        repo = Path(__file__).resolve().parents[1]
        if args.pid is not None:
            if args.pid <= 0:
                raise ValueError
            process = Path("/proc") / str(args.pid)
            environment = {}
            for item in (process / "environ").read_bytes().split(b"\0"):
                if b"=" in item:
                    name, value = item.split(b"=", 1)
                    environment[name.decode("utf-8", "surrogateescape")] = value.decode("utf-8", "surrogateescape")
            os.chdir((process / "cwd").resolve(strict=True))
            os.environ.clear()
            os.environ.update(environment)
        sys.path.insert(0, str(repo))
        from app.core.config import Settings, DEVELOPMENT_SECRET_KEY

        settings = Settings()
        secret = settings.SECRET_KEY.strip()
        checks = {
            "production_mode": settings.APP_ENV.strip().lower() in {"production", "prod"},
            "key_present": bool(secret),
            "key_not_default": secret != DEVELOPMENT_SECRET_KEY,
            "key_min_length": len(secret.encode("utf-8")) >= 32,
        }
        env_file = Path(".env")
        report = {
            "checks": checks,
            "baseline_passed": all(checks.values()),
            "env_file_present": env_file.is_file(),
            "env_private_permissions": (env_file.stat().st_mode & 0o077 == 0) if env_file.is_file() else None,
            "aws_static_credentials_in_process": any(
                bool(os.environ.get(name)) for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
            ),
        }
        print(json.dumps(report))
        return 0 if report["baseline_passed"] else 1
    except Exception as error:
        # Settings errors can embed secret input. Do not print str(error), a
        # traceback, an environment dump, or a fingerprint of the key.
        print(json.dumps({"status": "unverified", "reason": type(error).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
