"""Private subprocess entry point; controlled inputs from the supervisor only."""
import json
from pathlib import Path
import sys

from .backend import AutoCAD
from .records import digest
from .supervisor import atomic_json, backend_fingerprint, classify


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    output = Path(sys.argv[2])
    try:
        if backend_fingerprint() != request["backend_sha256"]:
            raise ValueError("Native backend changed before execution")
        source = Path(request["source"])
        if digest(source) != request["source_sha256"]:
            raise ValueError("Source fingerprint changed before execution")
        adapter = AutoCAD(expected_year=request.get("year"))
        destination = Path(request["destination"])
        if request["operation"] == "publish":
            result = adapter.publish(source, destination, request.get("sheet"),
                                     verify_native=request.get("verify_native", False))
        elif request["operation"] == "readback":
            result = {"readback": str(adapter.readback(source, destination))}
        else:
            raise ValueError("Unknown native operation")
        atomic_json(output, {"ok": True, "result": result})
        return 0
    except Exception as exc:
        atomic_json(output, {"ok": False, "category": classify(exc), "error": str(exc),
                            "type": type(exc).__name__})
        return 1


if __name__ == "__main__":
    sys.exit(main())
