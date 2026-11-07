"""All financial values in these tests are SYNTHETIC."""
import copy
import json
from pathlib import Path

import networkx as nx
import pandas as pd
import pytest

from app.cli import main
from app.core.models import DataError
from app.datasets.bis import load_bis, period_id
from app.datasets.io import read_table
from app.graph.builder import build_graph, graph_payload
from app.graph.statistics import statistics

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'data/demo/observations.csv'
MANIFEST = ROOT / 'data/demo/manifest.json'


def changed(tmp_path, column, value, row=0):
    frame = read_table(DEMO)
    frame.loc[row, column] = value
    path = tmp_path / 'changed.csv'
    frame.to_csv(path, index=False)
    return path


def test_csv_preserves_namibia_and_identifier(tmp_path):
    path = tmp_path / 'ids.csv'
    path.write_text('country,id\nNA,001\n', encoding='utf-8')
    assert read_table(path).iloc[0].to_dict() == {'country': 'NA', 'id': '001'}


def test_parquet_matches_csv(tmp_path):
    path = tmp_path / 'demo.parquet'
    read_table(DEMO).to_parquet(path, index=False)
    assert read_table(path).to_dict('records') == read_table(DEMO).to_dict('records')
    a = load_bis(DEMO, MANIFEST, '2025Q4')
    b = load_bis(path, MANIFEST, '2025-Q4')
    assert a.edges == b.edges
    assert b.report.valid


def test_column_mapping(tmp_path):
    frame = read_table(DEMO).rename(columns={'OBS_VALUE': 'amount'})
    path = tmp_path / 'mapped.csv'
    frame.to_csv(path, index=False)
    assert not load_bis(path, MANIFEST, '2025-Q4').report.valid
    data = load_bis(path, MANIFEST, '2025-Q4', {'amount': 'OBS_VALUE'})
    assert data.report.valid
    assert data.edges[0]['exposure'] == 10


@pytest.mark.parametrize('column,value,code', [
    ('OBS_VALUE', '-1', 'negative_weight'), ('OBS_VALUE', '0', 'zero_weight'),
    ('OBS_VALUE', 'oops', 'missing_or_nonnumeric_weight'),
    ('OBS_VALUE', 'NaN', 'missing_or_nonnumeric_weight'),
    ('OBS_VALUE', 'inf', 'missing_or_nonnumeric_weight'),
    ('L_CP_COUNTRY', 'US', 'self_loop'), ('L_CP_COUNTRY', 'XX', 'country_code'),
    ('TIME_PERIOD', '2025-Q5', 'period'), ('UNIT_MULT', '3', 'unit'),
    ('UNIT_MEASURE', '', 'unit'), ('OBS_CONF', 'C', 'nonpublic_observation'),
    ('OBS_STATUS', 'Q', 'observation_status')])
def test_invalid_data_fails_without_graph(tmp_path, column, value, code):
    data = load_bis(changed(tmp_path, column, value), MANIFEST, '2025-Q4')
    assert code in {issue['code'] for issue in data.report.issues}
    with pytest.raises(DataError):
        build_graph(data)


def test_duplicate_pair_never_overwritten(tmp_path):
    frame = read_table(DEMO)
    path = tmp_path / 'duplicates.csv'
    pd.concat([frame, frame.iloc[[0]]]).to_csv(path, index=False)
    data = load_bis(path, MANIFEST, '2025-Q4')
    assert not data.report.valid
    assert any(i['code'] == 'duplicate_edge' for i in data.report.issues)


def test_missing_reference_and_duplicate_node():
    data = load_bis(DEMO, MANIFEST, '2025-Q4')
    data.edges[0]['target'] = 'ZZ'
    data.nodes.append(copy.deepcopy(data.nodes[0]))
    with pytest.raises(DataError):
        build_graph(data)
    assert {'missing_reference', 'duplicate_node'} <= {i['code'] for i in data.report.issues}


def test_explicit_exclusion_is_audited_and_nodes_preserved(tmp_path):
    data = load_bis(changed(tmp_path, 'OBS_VALUE', 'NaN'), MANIFEST, '2025-Q4',
                    missing_policy='exclude')
    assert data.report.valid and len(data.edges) == 2 and len(data.nodes) == 3
    assert any(x['operation'] == 'exclude_unavailable' for x in data.report.transformations)
    graph = build_graph(data)
    assert not graph.has_edge('US', 'GB')


def test_zero_exclusion_and_loop_keep(tmp_path):
    data = load_bis(changed(tmp_path, 'OBS_VALUE', '0'), MANIFEST, '2025-Q4', zero_policy='exclude')
    assert data.report.valid and len(data.edges) == 2
    data = load_bis(changed(tmp_path, 'L_CP_COUNTRY', 'US'), MANIFEST, '2025-Q4', self_loop_policy='keep')
    assert nx.number_of_selfloops(build_graph(data)) == 1


def test_direction_strength_statistics_and_provenance():
    data = load_bis(DEMO, MANIFEST, '2025-Q4')
    graph = build_graph(data)
    assert graph.is_directed()
    assert graph.graph['debtor_scope'] == 'all_sectors'
    assert graph.nodes['US']['entity_type'] == 'country_or_territory'
    assert graph['US']['GB']['exposure'] == 10
    assert graph['GB']['US']['exposure'] == 4
    assert graph['US']['GB']['source_metadata']['original_fields']['OBS_VALUE'] == '10'
    assert graph.nodes['US']['available_financial_features'] == {}
    result = statistics(graph)
    assert result['node_count'] == 3 and result['edge_count'] == 3
    assert result['density'] == .5 and result['self_loop_count'] == 0
    assert result['nodes']['GB']['in_strength'] == 10
    assert result['nodes']['GB']['out_strength'] == 10
    assert result['weakly_connected_components']['count'] == 1
    assert result['strongly_connected_components']['count'] == 2
    assert result['weight_distribution']['mean'] == pytest.approx(20 / 3)
    assert graph.graph['provenance']['data_kind'] == 'synthetic'


def test_reproducible_graph():
    a = build_graph(load_bis(DEMO, MANIFEST, '2025-Q4'))
    b = build_graph(load_bis(DEMO, MANIFEST, '2025-Q4'))
    assert graph_payload(a) == graph_payload(b)
    assert statistics(a) == statistics(b)


def test_projection_no_double_count(tmp_path):
    frame = read_table(DEMO)
    extra = frame.iloc[[0]].copy()
    extra['L_CP_SECTOR'] = 'B'  # bank-sector subtotal must not be added to all sectors
    aggregate = frame.iloc[[0]].copy()
    aggregate['L_CP_COUNTRY'] = '5J'
    path = tmp_path / 'mixed.csv'
    pd.concat([frame, extra, aggregate]).to_csv(path, index=False)
    data = load_bis(path, MANIFEST, '2025-Q4')
    assert data.report.valid and len(data.edges) == 3
    assert data.report.transformations[-2]['excluded_counts'] == {
        'outside_profile': 1, 'aggregate_or_unallocated_area': 1}


def test_manifest_hash_mismatch(tmp_path):
    metadata = json.loads(MANIFEST.read_text())
    metadata['sha256'] = '0' * 64
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(metadata))
    assert not load_bis(DEMO, path, '2025-Q4').report.valid


def test_period_and_empty_selection():
    assert period_id('2025Q4') == '2025-Q4'
    with pytest.raises(DataError):
        period_id('2025')
    assert not load_bis(DEMO, MANIFEST, '2020-Q1').report.valid


@pytest.mark.parametrize('command', ['validate', 'build', 'stats'])
def test_cli_success(tmp_path, command):
    assert main([command, '--input', str(DEMO), '--manifest', str(MANIFEST),
                 '--period', '2025-Q4', '--output', str(tmp_path)]) == 0
    assert json.loads((tmp_path / 'validation-report.json').read_text())['valid']
    if command != 'validate':
        assert json.loads((tmp_path / 'statistics.json').read_text())['edge_count'] == 3


def test_cli_failure_report_and_no_graph(tmp_path):
    path = changed(tmp_path, 'OBS_VALUE', '-1')
    out = tmp_path / 'results'
    args = ['build', '--input', str(path), '--manifest', str(MANIFEST),
            '--period', '2025-Q4', '--output', str(out)]
    assert main(args) == 2
    assert not (out / 'graph.json').exists()
    assert not json.loads((out / 'validation-report.json').read_text())['valid']
    assert main(args) == 2


def test_unreadable_and_unsupported_table(tmp_path):
    for path in (tmp_path / 'missing.csv', tmp_path / 'file.xlsx'):
        with pytest.raises(DataError):
            read_table(path)


def test_duplicate_csv_headers(tmp_path):
    path = tmp_path / 'duplicate.csv'
    path.write_text('OBS_VALUE,OBS_VALUE\n1,2\n')
    with pytest.raises(DataError):
        read_table(path)


def test_exclude_policy_does_not_hide_corrupt_numbers(tmp_path):
    data = load_bis(changed(tmp_path, 'OBS_VALUE', 'oops'), MANIFEST, '2025-Q4', missing_policy='exclude')
    assert not data.report.valid


def test_all_missing_is_not_a_zero_exposure_graph(tmp_path):
    frame = read_table(DEMO)
    frame['OBS_VALUE'] = 'NaN'
    path = tmp_path / 'unavailable.csv'
    frame.to_csv(path, index=False)
    data = load_bis(path, MANIFEST, '2025-Q4', missing_policy='exclude')
    assert not data.report.valid
    assert any(i['code'] == 'empty_observed_graph' for i in data.report.issues)
