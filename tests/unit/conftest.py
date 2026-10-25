from __future__ import annotations

import stat
import textwrap
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_machine_environment(monkeypatch):
    for name in (
        "DOTFILES_UPDATE_STATE",
        "DOTFILES_UPDATE_LAST_CHECK",
        "MACHINE_PROFILE",
        "MACHINE_PROFILE_NAME",
        "MACHINE_APPLIED_HOST_FILE",
        "MACHINE_STATE_DIR",
        "MACHINE_SSH_KEY",
        "MISE_LOCAL_CONFIG",
        "BW_SESSION",
        "MACHINE_IN_DOCKER",
    ):
        monkeypatch.delenv(name, raising=False)


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
            import json, os, sys
            from pathlib import Path
            STORE = Path({str(store)!r})
            data = json.loads(STORE.read_text() or "{{}}")
            args = sys.argv[1:]
            if not args:
                raise SystemExit(1)
            if args[0] == "status":
                # like bw: an exported BW_SESSION also counts as unlocked
                unlocked = data.get("_session") or os.environ.get("BW_SESSION")
                print(json.dumps({{"status": "unlocked" if unlocked else "unauthenticated"}}))
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
            items = data.setdefault("items", {{}})
            def matching(key):
                return [
                    (k, item) for k, item in items.items()
                    if key in (k, item.get("id"), item.get("name"))
                ]
            if args[0] == "list" and args[1] == "items":
                search = args[args.index("--search") + 1] if "--search" in args else ""
                print(json.dumps([
                    item for k, item in items.items()
                    if search in str(item.get("name", k))
                ]))
                raise SystemExit(0)
            if args[0] == "get" and args[1] == "item":
                name = args[2]
                found = matching(name)
                if len(found) != 1:
                    raise SystemExit(1)
                if "--raw" in args:
                    print(json.dumps(found[0][1]))
                else:
                    print(name)
                raise SystemExit(0)
            if args[0] == "create" and args[1] == "item":
                if os.environ.get("FAKE_BW_CREATE_FAILS"):
                    raise SystemExit(1)
                payload = json.loads(sys.stdin.read())
                payload["id"] = f"id-{{len(items) + len(data.get('trash', {{}})) + 1}}"
                items[payload["id"]] = payload
                STORE.write_text(json.dumps(data))
                print(json.dumps(payload))
                raise SystemExit(0)
            if args[0] == "edit" and args[1] == "item":
                payload = json.loads(sys.stdin.read())
                found = matching(args[2])
                key = found[0][0] if found else payload["name"]
                items[key] = payload
                STORE.write_text(json.dumps(data))
                print(json.dumps(payload))
                raise SystemExit(0)
            if args[0] == "delete" and args[1] == "item":
                found = matching(args[2])
                if len(found) != 1:
                    raise SystemExit(1)
                trash = data.setdefault("trash", {{}})
                trash[found[0][0]] = items.pop(found[0][0])
                if "--permanent" in args:
                    trash.pop(found[0][0])
                STORE.write_text(json.dumps(data))
                raise SystemExit(0)
            raise SystemExit(0)
            """
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, store
