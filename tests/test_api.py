from fastapi.testclient import TestClient

from app import app
from src.api.routes import get_audit_store, set_audit_store
from src.models.ingestion import AttachmentReference, EmailRecord
from src.pipeline.orchestrator import PipelineOrchestrator
from src.store.audit_store import AuditStore

client = TestClient(app)

_SI = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 2
Gross Weight: 22,000 KGS
"""

_BL_MATCH = _SI

_BL_MISMATCH = """
Shipper: ACME EXPORTS LTD 123 INDUSTRIAL WAY SINGAPORE 068896
Consignee: GLOBAL IMPORTERS LLC 456 HARBOR ROAD ROTTERDAM NETHERLANDS
Notify Party: SAME AS CONSIGNEE
Port of Loading: SHANGHAI (CNSHA)
Port of Discharge: ROTTERDAM (NLRTM)
Container Count: 4
Gross Weight: 22,000 KGS
"""


def _audit_case(email_id: str, bl_text: str):
    previous = get_audit_store()
    store = AuditStore()
    orchestrator = PipelineOrchestrator(audit_store=store)
    set_audit_store(store)
    email = EmailRecord(
        email_id=email_id,
        sender="shipping@example.com",
        subject="Please compare SI vs Draft BL",
        body="Please verify the draft BL against the shipping instruction.",
        attachments=[
            AttachmentReference(document_id=f"{email_id}_SI.txt", path=f"{email_id}_SI.txt"),
            AttachmentReference(document_id=f"{email_id}_BL.txt", path=f"{email_id}_BL.txt"),
        ],
    )
    orchestrator.process_email(
        email,
        document_texts={
            f"{email_id}_SI.txt": _SI,
            f"{email_id}_BL.txt": bl_text,
        },
    )
    try:
        return client.get(f"/audit/{email_id}")
    finally:
        set_audit_store(previous)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "SDOC Shipping Document Verification Engine"
    assert "total_audited_emails" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_get_single_audit_ok():
    response = _audit_case("synthetic_match", _BL_MATCH)
    assert response.status_code == 200
    data = response.json()
    assert data["email_id"] == "synthetic_match"
    assert data["classification"]["category"] == "document_comparison"
    assert data["mismatch_detected"] is False
    assert data["outcome"] == "MATCH"


def test_get_single_audit_mismatch():
    response = _audit_case("synthetic_mismatch", _BL_MISMATCH)
    assert response.status_code == 200
    data = response.json()
    assert data["email_id"] == "synthetic_mismatch"
    assert data["mismatch_detected"] is True
    assert any(d["field"] == "container_count" for d in data["discrepancies"])


def test_dynamic_verify_endpoint():
    req = {
        "email_id": "test_verification",
        "si_text": "Shipper: APRIL FAR EAST LTD\nConsignee: MOORIM SP CO., LTD\nNotify: UAB NOVAKOPA\nPort of Loading: PORT KLANG (MYPKG)\nPort of Discharge: CALLAO (PECLL)\nContainer Count: Three (3) Containers\nGross Weight: 25 MT",
        "bl_text": "Shipper: APRIL FAR EAST LIMITED\nConsignee: MOORIM SP CO., LTD.\nNotify Party: UAB NOVAKOPA\nLoad Port: PORT KLANG (MYPKG)\nDischarge Port: CALLAO (PECLL)\nTotal Containers: 4 x 40 HC\nG.W.: 25,000 KG",
    }
    response = client.post("/verify", json=req)
    assert response.status_code == 200
    data = response.json()
    assert data["mismatch_detected"] is True
    assert len(data["discrepancies"]) == 1
    assert data["discrepancies"][0]["field"] == "container_count"
    assert data["discrepancies"][0]["si_value"] == 3
    assert data["discrepancies"][0]["bl_value"] == 4
