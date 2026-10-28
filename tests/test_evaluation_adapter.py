"""T13: synthetic canonical records -> official output, without upstream inference."""
from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app import app
from src.adapters.evaluation_adapter import EvaluationAdapter, ExportBlockedException, ExportService
from src.api.routes import get_audit_store
from src.models.audit import AuditRecord, ErrorResponse, SubmissionRecord
from src.models.extraction import FIELD_NAMES
from src.store.audit_store import AuditStore


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = json.loads((ROOT / 'tests/fixtures/data_contract_examples.json').read_text(encoding='utf-8'))
REVIEW_CASES = ROOT / 'tests/fixtures/review/cases'
OFFICIAL_KEYS = {'category', 'status', 'review_reason', 'defect_fields', 'has_defect'}


def synthetic_record(example='complete_match', email_id=None, defects=()):
    data = deepcopy(EXAMPLES[example]['payload'])
    if email_id is not None:
        data['email_id'] = data['email']['email_id'] = email_id
        for evidence in data['evidence']:
            if evidence['source_type'] == 'email':
                evidence['source_id'] = email_id
    if defects:
        bl = next(e for e in data['extractions'] if e['role'] == 'BL')
        data['discrepancies'] = []
        for comparison in data['partial_result']['comparisons']:
            if comparison['field'] not in defects:
                continue
            field = comparison['field']
            changed = 9 if field == 'container_count' else '999.125' if field == 'gross_weight_kg' else 'SYNTHETIC DIFFERENT VALUE'
            extracted = bl['fields'][field]
            extracted['normalized']['value'] = changed
            candidate = extracted['candidates'][extracted['selected_candidate']]
            candidate['raw_value'] = str(changed)
            for evidence in data['evidence']:
                if evidence['evidence_id'] in candidate['evidence_ids']:
                    evidence['quote'] = str(changed)
            comparison['bl_value'] = changed
            comparison['outcome'] = 'MISMATCH'
            data['discrepancies'].append({k: comparison[k] for k in ('field', 'si_value', 'bl_value')})
        data['outcome'] = 'MISMATCH'
        data['mismatch_detected'] = True
        data['result_summary'] = 'Mismatches detected: ' + '; '.join(
            f"{d['field']} (SI: {d['si_value']} / BL: {d['bl_value']})" for d in data['discrepancies']
        )
    return AuditRecord.model_validate(data)


@pytest.mark.parametrize(('category', 'official'), [
    ('document_comparison', 'BL_COMPARISON'),
    ('new_shipping_instruction', 'SI_REQUEST'),
    ('invoice_query', 'INVOICE_QUERY'),
    ('general', 'GENERAL'),
    ('spam', 'SPAM'),
], ids=lambda value: value)
def test_eval_map_001_categories_and_noncomparison_coverage(category, official):
    record = synthetic_record('complete_match' if category == 'document_comparison' else 'non_comparison')
    record.classification.category = category
    result = EvaluationAdapter().to_submission_record(record)
    assert result.model_dump() == dict(category=official, status='OK', review_reason=None, defect_fields=[], has_defect=False)
    if category != 'document_comparison':
        assert record.outcome == 'NOT_APPLICABLE'


@pytest.mark.parametrize('example', ['unresolved_classification'], ids=['EVAL-MAP-002'])
def test_eval_map_002_null_category_blocks(example):
    record = synthetic_record(example)
    with pytest.raises(ExportBlockedException) as caught:
        EvaluationAdapter().to_submission_record(record)
    assert caught.value.blocking_emails == [record.email_id]
    assert record.classification.category is None


@pytest.mark.parametrize('example', ['complete_match'], ids=['EVAL-MAP-003'])
def test_eval_map_003_clean_match_exact_official_shape(example):
    result = EvaluationAdapter().to_submission_record(synthetic_record(example)).model_dump()
    assert set(result) == OFFICIAL_KEYS
    assert result == dict(category='BL_COMPARISON', status='OK', review_reason=None, defect_fields=[], has_defect=False)


@pytest.mark.parametrize('fields', [('container_count',)], ids=['EVAL-MAP-004'])
def test_eval_map_004_single_discrepancy(fields):
    result = EvaluationAdapter().to_submission_record(synthetic_record(defects=fields))
    assert result.model_dump() == dict(category='BL_COMPARISON', status='MISMATCH', review_reason=None, defect_fields=['container_count'], has_defect=True)


@pytest.mark.parametrize('fields', [FIELD_NAMES], ids=['EVAL-MAP-005'])
def test_eval_map_005_seven_field_identifiers(fields):
    result = EvaluationAdapter().to_submission_record(synthetic_record(defects=fields))
    assert result.defect_fields == sorted(FIELD_NAMES)
    assert set(result.model_dump()) == OFFICIAL_KEYS


@pytest.mark.parametrize('fields', [('shipper', 'gross_weight_kg')], ids=['EVAL-MAP-006'])
def test_eval_map_006_deterministic_sorting(fields):
    record = synthetic_record(defects=fields)
    before = record.model_dump_json()
    result = EvaluationAdapter().to_submission_record(record)
    assert result.defect_fields == ['gross_weight_kg', 'shipper']
    assert result == EvaluationAdapter().to_submission_record(record)
    assert record.model_dump_json() == before


@pytest.mark.parametrize('path', sorted(REVIEW_CASES.glob('*.json')), ids=lambda path: f'EVAL-MAP-007-{path.stem}')
def test_eval_map_007_every_review_case_blocks_without_mutation(path):
    record = AuditRecord.model_validate_json(path.read_text(encoding='utf-8'))
    before = record.model_dump_json()
    with pytest.raises(ExportBlockedException) as caught:
        EvaluationAdapter().to_submission_record(record)
    assert caught.value.blocking_emails == [record.email_id]
    assert record.model_dump_json() == before


@pytest.fixture
def api_client():
    store = AuditStore()
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_audit_store] = lambda: store
    with TestClient(app) as client:
        yield client, store
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)


@pytest.mark.parametrize('case', ['resolved-batch'], ids=['API-EXP-001'])
def test_api_exp_001_actual_service_retains_all_categories(api_client, case):
    client, store = api_client
    records = [synthetic_record(email_id='synthetic-match'), synthetic_record(email_id='synthetic-mismatch', defects=('container_count',))]
    for category in ('new_shipping_instruction', 'invoice_query', 'general', 'spam'):
        record = synthetic_record('non_comparison', email_id=f'synthetic-{category}')
        record.classification.category = category
        records.append(record)
    for record in records:
        store.save(record)
    response = client.get('/submission')
    assert response.status_code == 200
    assert set(response.json()) == {r.email_id for r in records}
    assert response.json() == ExportService().export(records)
    for item in response.json().values():
        assert set(item) == OFFICIAL_KEYS
        SubmissionRecord.model_validate(item)
    assert response.json()['synthetic-mismatch']['defect_fields'] == ['container_count']


@pytest.mark.parametrize('example', ['missing_attachment', 'unresolved_classification'], ids=['API-EXP-002-known-category', 'API-EXP-002-null-category'])
def test_api_exp_002_nine_safe_one_review_blocks_entire_batch(api_client, example):
    client, store = api_client
    for i in range(9):
        store.save(synthetic_record(email_id=f'synthetic-safe-{i}'))
    blocked = synthetic_record(example)
    store.save(blocked)
    before = blocked.model_dump_json()
    response = client.get('/submission')
    assert response.status_code == 409
    expected = ErrorResponse(code='EXPORT_BLOCKED', message='Cannot export submission while cases remain in NEEDS_REVIEW', details=[f'Unexportable email: {blocked.email_id}'], retryable=False, blocking_emails=[blocked.email_id]).model_dump()
    assert response.json() == expected
    assert not any(key.startswith('synthetic-safe') for key in response.json())
    assert blocked.model_dump_json() == before


def test_batch_preflight_blocks_before_any_mapping_and_lists_all_blockers():
    adapter = EvaluationAdapter()
    adapter.to_submission_record = Mock(wraps=adapter.to_submission_record)
    blocked = [synthetic_record('missing_attachment'), synthetic_record('unresolved_classification')]
    with pytest.raises(ExportBlockedException) as caught:
        ExportService(adapter).export([synthetic_record(), *blocked])
    assert caught.value.blocking_emails == sorted(r.email_id for r in blocked)
    adapter.to_submission_record.assert_not_called()


def test_batch_determinism_coverage_and_duplicate_protection():
    a, b = synthetic_record(email_id='synthetic-a'), synthetic_record('non_comparison', email_id='synthetic-b')
    service = ExportService()
    assert json.dumps(service.export([a, b])) == json.dumps(service.export(iter([b, a])))
    with pytest.raises(ExportBlockedException):
        service.export([a, a])
    with pytest.raises(ExportBlockedException) as caught:
        service.export([a], expected_email_ids=[a.email_id, b.email_id])
    assert caught.value.blocking_emails == [b.email_id]


def test_adapter_uses_decisions_only_and_preserves_decimal(monkeypatch):
    record = synthetic_record(defects=('gross_weight_kg',))
    for extraction in record.extractions:
        value = extraction.fields['gross_weight_kg'].normalized
        value.value = Decimal(str(value.value))
    before = record.model_dump_json()
    # Neither a new comparison nor model revalidation may be needed to export a
    # validated record. The adapter consumes the already-decided discrepancies.
    monkeypatch.setattr(AuditRecord, 'model_validate', Mock(side_effect=AssertionError('no upstream revalidation')))
    result = EvaluationAdapter().to_submission_record(record).model_dump()
    assert result['defect_fields'] == ['gross_weight_kg']
    assert not any(isinstance(v, (float, Decimal)) for v in result.values())
    assert record.model_dump_json() == before


def test_legacy_wrappers_delegate_to_authoritative_boundary(monkeypatch):
    from src.pipeline.validator import validate_submission_dict
    from src.run_pipeline import audit_record_to_competition_dict
    record = synthetic_record()
    spy = Mock(wraps=EvaluationAdapter.to_submission_record)
    monkeypatch.setattr(EvaluationAdapter, 'to_submission_record', lambda self, rec: spy(self, rec))
    exported = audit_record_to_competition_dict(record)
    assert spy.call_count == 1
    assert validate_submission_dict({record.email_id: exported}, {record.email_id: None}) == (True, [])
    invalid = {**exported, 'unexpected': 'not in official schema'}
    assert validate_submission_dict({record.email_id: invalid}, {record.email_id: None})[0] is False
    with pytest.raises(ExportBlockedException):
        audit_record_to_competition_dict(synthetic_record('missing_attachment'))


def test_cli_block_retains_audit_and_never_fills_sample_defaults(tmp_path, monkeypatch):
    from src import run_pipeline as runner
    monkeypatch.chdir(tmp_path)
    bundle = tmp_path / 'synthetic-input'
    bundle.mkdir()
    records = [synthetic_record(email_id='synthetic-first'), synthetic_record('missing_attachment', email_id='synthetic-second')]
    monkeypatch.setattr(runner, 'load_inbox_emails', lambda _: [{'email_id': r.email_id} for r in records])
    fake_orchestrator = Mock()
    fake_orchestrator.process_email.side_effect = records
    monkeypatch.setattr(runner, 'PipelineOrchestrator', lambda **_: fake_orchestrator)
    output = tmp_path / 'submission.json'
    output.write_text('previous completed export', encoding='utf-8')
    with pytest.raises(ExportBlockedException):
        runner.run_pipeline(str(bundle), str(output), str(tmp_path / 'audit.json'))
    assert output.read_text(encoding='utf-8') == 'previous completed export'
    assert len(json.loads((tmp_path / 'audit.json').read_text(encoding='utf-8'))) == 2
    fake_orchestrator.process_email.side_effect = records
    with pytest.raises(ExportBlockedException):
        runner.run_pipeline(str(bundle), str(output), str(tmp_path / 'limited-audit.json'), limit=1)
    assert output.read_text(encoding='utf-8') == 'previous completed export'


def test_empty_api_store_is_not_an_empty_success(api_client):
    client, _ = api_client
    assert client.get('/submission').status_code == 404
