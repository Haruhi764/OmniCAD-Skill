"""Bounded worker execution; never terminates or restarts the CAD application."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

from .records import digest


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


@contextmanager
def exclusive(path):
    with Path(path).open("a+b") as stream:
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if sys.platform == "win32":
            import msvcrt
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as e:
                raise RuntimeError("Native execution lock is busy") from e
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as e:
                raise RuntimeError("Native execution lock is busy") from e
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def default_state():
    # One circuit and lock for the current user's CAD session, regardless of project.
    return Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "OmniCAD" / "native-v12"


def classify(error):
    code = getattr(error, "hresult", 0) or 0
    hexcode = code & 0xffffffff
    if hexcode in (0x800706BA, 0x800706BE, 0x80010108):
        return "disconnected"
    if hexcode in (0x80010001, 0x8001010A):
        return "busy"
    return "worker_error"


def _fingerprint(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def backend_fingerprint():
    """Invalidate native reuse when code affecting native publication changes."""
    root=Path(__file__).resolve().parent
    names=("backend.py","capabilities.py","native_worker.py","supervisor.py",
           "dxf.py","records.py","pdfquality.py")
    return _fingerprint({name:digest(root/name) for name in names})


def _artifact_hashes(result, destination, request):
    required = ("dwg", "readback") if request["operation"] == "publish" else ("readback",)
    if request.get("sheet"):
        required += ("pdf",)
        if request.get("verify_native"):
            required += ("replot",)
    if any(not result.get(key) for key in required):
        raise ValueError("Worker omitted required artifacts")
    hashes = {}
    for key in (*required, "pdf", "replot"):
        if key in hashes or not result.get(key):
            continue
        path = Path(result[key]).resolve()
        if path.parent != destination or not path.is_file() or not path.stat().st_size:
            raise ValueError("Missing, empty, or out-of-scope native artifact: " + key)
        hashes[key] = digest(path)
    return hashes


def execute(request, state=None, timeout=180, budget=None, runner=None, global_state=None):
    """One worker/job; hash-bound checkpoints; fail closed after unknown native state."""
    if not 1 <= timeout <= 1800 or (budget is not None and budget < 1):
        raise ValueError("Invalid native timeout or budget")
    state = Path(state or default_state()).resolve()
    root = Path(global_state or default_state()).resolve()
    root.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    destination = Path(request["destination"]).resolve()
    source = Path(request["source"]).resolve()
    request = {**request, "source": str(source), "destination": str(destination),
               "source_sha256": digest(source), "protocol": 1,
               "backend_sha256": backend_fingerprint()}
    key = _fingerprint(request)
    checkpoint = state / (key + ".json")
    circuit = root / "circuit.json"
    counter = state / "usage.json"
    with exclusive(root / "native.lock"):
        if checkpoint.exists():
            prior = json.loads(checkpoint.read_text(encoding="utf-8"))
            if prior.get("status") == "succeeded":
                if _artifact_hashes(prior["result"], destination, request) != prior["hashes"]:
                    raise RuntimeError("Checkpoint artifact changed; use a new output directory")
                return prior["result"], {"reused": True, "checkpoint": str(checkpoint)}
            raise RuntimeError("Prior native job did not complete; preserve evidence and use a new output directory")
        if circuit.exists():
            raise RuntimeError("Native circuit is open; review CAD session and reset explicitly")
        if destination.exists():
            raise FileExistsError("Native output must be a new directory")
        usage = json.loads(counter.read_text(encoding="utf-8")) if counter.exists() else {"native_jobs": 0, "seconds": 0}
        if budget is not None and usage["native_jobs"] >= budget:
            raise RuntimeError("Native job budget exhausted")
        usage["native_jobs"] += 1
        atomic_json(counter, usage)
        atomic_json(checkpoint, {"status": "running", "request": request})
        atomic_json(circuit, {"reason": "in_progress_or_interrupted", "checkpoint": str(checkpoint)})
        started = time.perf_counter()
        reason = None
        try:
            if runner is None:
                result_path = state / (key + ".result.json")
                payload_path = state / (key + ".request.json")
                atomic_json(payload_path, request)
                with (state / (key + ".log")).open("wb") as log:
                    worker = subprocess.Popen([sys.executable, "-m", "omnicad.native_worker",
                                               str(payload_path), str(result_path)],
                                              stdout=log, stderr=subprocess.STDOUT)
                    try:
                        worker.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        worker.kill()  # Only our Python worker, never the CAD process.
                        worker.wait(timeout=10)
                        raise
                if not result_path.is_file():
                    raise RuntimeError("Native worker returned no structured result")
                response = json.loads(result_path.read_text(encoding="utf-8"))
                if worker.returncode or not response.get("ok"):
                    reason = response.get("category", "worker_error")
                    raise RuntimeError("Native worker: " + str(response))
                result = response["result"]
            else:
                result = runner(request)
            if digest(source) != request["source_sha256"]:
                raise RuntimeError("Original source changed during execution")
            hashes = _artifact_hashes(result, destination, request)
            atomic_json(checkpoint, {"status": "succeeded", "request": request,
                                     "result": result, "hashes": hashes})
            circuit.unlink()
            return result, {"reused": False, "checkpoint": str(checkpoint)}
        except Exception as exc:
            reason = reason or ("timeout" if isinstance(exc, subprocess.TimeoutExpired) else classify(exc))
            atomic_json(checkpoint, {"status": "failed", "request": request,
                                     "reason": reason, "error": str(exc)})
            atomic_json(circuit, {"reason": reason, "checkpoint": str(checkpoint)})
            raise RuntimeError(f"Native execution stopped ({reason}): {exc}") from exc
        finally:
            usage["seconds"] = round(usage["seconds"] + time.perf_counter() - started, 4)
            atomic_json(counter, usage)


def reset_circuit(confirmed=False, global_state=None):
    if not confirmed:
        raise ValueError("Review the CAD session and retained work before resetting the circuit")
    root = Path(global_state or default_state())
    root.mkdir(parents=True, exist_ok=True)
    with exclusive(root / "native.lock"):
        circuit = root / "circuit.json"
        if circuit.exists():
            circuit.rename(root / ("reviewed-" + uuid.uuid4().hex + ".json"))
