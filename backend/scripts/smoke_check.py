import json
import sys
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def _request(method: str, path: str, payload: dict | None = None, token: str | None = None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body_text = response.read().decode("utf-8")
            body = json.loads(body_text) if body_text else {}
            return response.status, body, None
    except urllib.error.HTTPError as exc:
        err_text = exc.read().decode("utf-8") if exc.fp else ""
        try:
            err_json = json.loads(err_text) if err_text else {}
        except Exception:
            err_json = {"raw": err_text}
        return exc.code, err_json, None
    except Exception as exc:  # noqa: BLE001
        return 0, {}, str(exc)


def _print_result(name: str, ok: bool, detail: str):
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}: {detail}")


def main() -> int:
    failures = 0

    # 1) Auth doctor
    status, body, err = _request("POST", "/api/auth/login", {"username": "dr.garcia", "password": "demo1234"})
    auth_ok = (status == 200 and "access_token" in body and not err)
    _print_result("auth_doctor_login", auth_ok, f"status={status}")
    if not auth_ok:
        failures += 1
        print(json.dumps(body, ensure_ascii=False))
        return 1
    doctor_token = body["access_token"]

    # 2) Reports process
    status, body, err = _request(
        "POST",
        "/api/reports/process",
        {
            "dictation_report": "RM de rodilla con patela alta, fisuras condrales grado II-III, sin derrame articular y meniscos conservados.",
            "patient_id": "PAT-002",
            "specialty": "Traumatologia",
        },
        doctor_token,
    )
    process_ok = (status == 200 and "humanized" in body and not err)
    _print_result("reports_process", process_ok, f"status={status}")
    if not process_ok:
        failures += 1
        print(json.dumps(body, ensure_ascii=False))

    # 3) Auth patient
    status, body, err = _request("POST", "/api/auth/login", {"username": "carolina.r", "password": "demo1234"})
    patient_auth_ok = (status == 200 and "access_token" in body and not err)
    _print_result("auth_patient_login", patient_auth_ok, f"status={status}")
    if not patient_auth_ok:
        failures += 1
        print(json.dumps(body, ensure_ascii=False))
        return 1
    patient_token = body["access_token"]

    # 4) Avatar greeting
    status, body, err = _request("GET", "/api/avatar/greeting/PAT-002", token=patient_token)
    greeting_ok = (status == 200 and isinstance(body.get("respuesta_voz"), str) and not err)
    _print_result("avatar_greeting", greeting_ok, f"status={status}")
    if not greeting_ok:
        failures += 1
        print(json.dumps(body, ensure_ascii=False))
    greeting_text = body.get("respuesta_voz", "") if isinstance(body, dict) else ""

    # 5) Avatar chat
    status, body, err = _request(
        "POST",
        "/api/avatar/chat",
        {
            "message": "Tengo miedo, me explicas el informe?",
            "patient_id": "PAT-002",
            "conversation_history": [{"role": "assistant", "content": greeting_text}],
        },
        patient_token,
    )
    avatar_chat_ok = (status == 200 and isinstance(body.get("respuesta_voz"), str) and not err)
    _print_result("avatar_chat", avatar_chat_ok, f"status={status}")
    if not avatar_chat_ok:
        failures += 1
        print(json.dumps(body, ensure_ascii=False))

    # 6) Integration diagnostics
    status, body, err = _request("GET", "/api/reports/integration/diagnostics", token=doctor_token)
    diagnostics_ok = (status == 200 and "status" in body and not err)
    _print_result("integration_diagnostics", diagnostics_ok, f"status={status}; diag_status={body.get('status') if isinstance(body, dict) else 'n/a'}")
    if not diagnostics_ok:
        failures += 1
        print(json.dumps(body, ensure_ascii=False))

    # 7) Idonia link smoke (expected to fail while external tenant is blocked)
    status, body, err = _request(
        "POST",
        "/api/reports/patients/PAT-002/idonia-link?resource=report",
        {},
        doctor_token,
    )
    idonia_ok = (status == 200)
    if idonia_ok:
        _print_result("idonia_link", True, f"status={status}")
    else:
        _print_result("idonia_link", False, f"status={status} (esperable en entorno bloqueado ICC)")

    print("\nResumen:")
    print(f"- Fallos bloqueantes locales: {failures}")
    if failures == 0:
        print("- Backend local operativo (auth/reports/avatar/diagnostics).")
    else:
        print("- Hay fallos locales a corregir.")

    return 0 if failures == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
