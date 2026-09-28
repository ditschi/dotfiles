from __future__ import annotations

import stat
import textwrap
from pathlib import Path

import pytest


@pytest.fixture
def fake_bw(tmp_path: Path):
    """Minimal bw stub: unlock returns session; get/create/edit items in a JSON store."""
    store = tmp_path / "bw-store.json"
    store.write_text("{}", encoding="utf-8")
    script = tmp_path / "bw"
    script.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, sys
            from pathlib import Path
            STORE = Path({str(store)!r})
            data = json.loads(STORE.read_text() or "{{}}")
            args = sys.argv[1:]
            if not args:
                raise SystemExit(1)
            if args[0] == "status":
                print(json.dumps({{"status": "unlocked" if data.get("_session") else "unauthenticated"}}))
                raise SystemExit(0)
            if args[0] == "unlock" and "--raw" in args:
                data["_session"] = "fake-session"
                STORE.write_text(json.dumps(data))
                print("fake-session")
                raise SystemExit(0)
            if args[0] == "login":
                data["_session"] = "fake-session"
                STORE.write_text(json.dumps(data))
                raise SystemExit(0)
            if args[0] == "sync":
                raise SystemExit(0)
            if args[0] == "encode":
                print(sys.stdin.read(), end="")
                raise SystemExit(0)
            if args[0] == "get" and args[1] == "item":
                name = args[2]
                item = data.get("items", {{}}).get(name)
                if not item:
                    raise SystemExit(1)
                if "--raw" in args:
                    print(json.dumps(item))
                else:
                    print(name)
                raise SystemExit(0)
            if args[0] == "create" and args[1] == "item":
                payload = json.loads(sys.stdin.read())
                items = data.setdefault("items", {{}})
                payload["id"] = payload.get("name", "id")
                items[payload["name"]] = payload
                STORE.write_text(json.dumps(data))
                print(json.dumps(payload))
                raise SystemExit(0)
            if args[0] == "edit" and args[1] == "item":
                payload = json.loads(sys.stdin.read())
                items = data.setdefault("items", {{}})
                items[payload["name"]] = payload
                STORE.write_text(json.dumps(data))
                print(json.dumps(payload))
                raise SystemExit(0)
            raise SystemExit(0)
            """
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, store
