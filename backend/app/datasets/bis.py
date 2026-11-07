"""BIS WS_LBS_D_PUB flat CSV adapter. No inferred bank-level exposures."""
import json
import math
import re
from pathlib import Path

from app.core.models import Dataset, Report, DataError
from app.datasets.io import read_table, read_manifest, sha256

PROFILE = dict(FREQ='Q', L_MEASURE='S', L_POSITION='C', L_INSTR='G',
               L_DENOM='TO1', L_CURR_TYPE='A', L_PARENT_CTY='5J',
               L_REP_BANK_TYPE='A', L_CP_SECTOR='A', L_POS_TYPE='N')
REQUIRED = set(PROFILE) | {'L_REP_CTY', 'L_CP_COUNTRY', 'TIME_PERIOD', 'OBS_VALUE',
                           'UNIT_MEASURE', 'UNIT_MULT', 'OBS_STATUS', 'OBS_CONF'}
STATUS = {'A', 'B', 'D', 'E', 'I', 'P', 'U'}


def period_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-?Q[1-4]', value):
        raise DataError(f'Invalid quarterly period: {value!r}; use YYYY-Q1..Q4.')
    return value[:4] + '-Q' + value[-1]


def load_bis(path: str | Path, manifest_path: str | Path, period: str,
             column_map: dict[str,str] | None = None, missing_policy: str = 'error',
             zero_policy: str = 'error', self_loop_policy: str = 'error') -> Dataset:
    period = period_id(period)
    if missing_policy not in ('error', 'exclude') or zero_policy not in ('error', 'exclude'):
        raise DataError('Missing/zero policies must be error or exclude.')
    if self_loop_policy not in ('error', 'keep'):
        raise DataError('Self-loop policy must be error or keep.')
    manifest = read_manifest(manifest_path)
    digest = sha256(path)
    provenance = dict(manifest, input_sha256=digest, adapter_version='bis-lbs-v1')
    report = Report(provenance, dict(profile=PROFILE, period=period,
        missing_policy=missing_policy, zero_policy=zero_policy,
        self_loop_policy=self_loop_policy, column_map=column_map or {}))
    if manifest.get('sha256') and manifest['sha256'] != digest:
        report.add('error', 'hash_mismatch', 'Input differs from manifest SHA-256.')
    frame = read_table(path)
    original_rows = frame.to_dict('records')
    if column_map:
        if any(k not in frame.columns for k in column_map):
            report.add('error', 'column_mapping', 'Mapping contains a missing source column.')
        frame = frame.rename(columns=column_map)
        report.transformations.append(dict(operation='column_mapping', mapping=column_map))
    report.input_rows = len(frame)
    absent = sorted(REQUIRED - set(frame.columns))
    if absent or frame.columns.duplicated().any():
        report.add('error', 'schema', f'Missing fields: {absent}; duplicate columns are forbidden.')
        return Dataset([], [], report, period)
    codes = json.loads(Path(__file__).with_name('bis_codes.json').read_text(encoding='utf-8'))
    countries = codes['countries']
    records, nodes, seen, exclusions = [], {}, set(), {}

    def excluded(reason, row):
        exclusions[reason] = exclusions.get(reason, 0) + 1

    mapped_rows = frame.to_dict('records') if column_map else original_rows
    for number, raw in enumerate(mapped_rows, start=2):
        # Original fields retained, including values excluded from this projection.
        if any(raw[k] != value for k, value in PROFILE.items()):
            excluded('outside_profile', number)
            continue
        try:
            row_period = period_id(raw['TIME_PERIOD'])
        except DataError as exc:
            report.add('error', 'period', str(exc), number)
            continue
        if row_period != period:
            excluded('other_period', number)
            continue
        source, target = raw['L_REP_CTY'], raw['L_CP_COUNTRY']
        if source not in countries or target not in countries:
            if source in codes['areas'] and target in codes['areas']:
                excluded('aggregate_or_unallocated_area', number)
            else:
                report.add('error', 'country_code', f'Unknown area: {source}, {target}', number)
            continue
        report.selected_rows += 1
        key = (source, target)
        if key in seen:
            report.add('error', 'duplicate_edge', f'Duplicate pair {key}; not summed.', number)
        seen.add(key)
        if raw['UNIT_MEASURE'] != 'USD' or raw['UNIT_MULT'] != '6':
            report.add('error', 'unit', 'Expected UNIT_MEASURE=USD, UNIT_MULT=6 (million USD).', number)
        for code in (source, target):
            nodes[code] = dict(node_id=code, source_identifier=code,
                entity_type='country_or_territory', dataset_id=manifest['dataset_id'],
                period=period, available_financial_features={},
                source_metadata=dict(country_name=countries[code],
                    outgoing_scope='resident_reporting_banks', incoming_scope='all_counterparty_sectors'))
        if raw['OBS_CONF'] != 'F':
            severity = 'warning' if missing_policy == 'exclude' else 'error'
            report.add(severity, 'nonpublic_observation', 'Non-free observation is unavailable, never zero.', number)
            if missing_policy == 'exclude':
                report.transformations.append(dict(operation='exclude_nonpublic', row=number))
            continue
        try:
            exposure = float(raw['OBS_VALUE'])
            if not math.isfinite(exposure):
                raise ValueError()
        except (ValueError, TypeError):
            unavailable = raw['OBS_VALUE'].strip().lower() in ('', 'nan', 'na', 'n.a.', ':', '..')
            severity = 'warning' if missing_policy == 'exclude' and unavailable else 'error'
            report.add(severity, 'missing_or_nonnumeric_weight',
                       f'Unavailable/nonfinite observation: {raw["OBS_VALUE"]!r}', number)
            if severity == 'warning':
                report.transformations.append(dict(operation='exclude_unavailable', row=number))
            continue
        if raw['OBS_STATUS'] not in STATUS:
            report.add('error', 'observation_status', f'Unsupported status {raw["OBS_STATUS"]}', number)
        elif raw['OBS_STATUS'] != 'A':
            report.add('warning', 'observation_status', f'Source status: {raw["OBS_STATUS"]}', number)
        if exposure < 0:
            report.add('error', 'negative_weight', 'Negative stock exposure; never clipped or absolutized.', number)
        if exposure == 0:
            report.add('warning' if zero_policy == 'exclude' else 'error', 'zero_weight',
                       'Zero stock observation.', number)
            if zero_policy == 'exclude':
                report.transformations.append(dict(operation='exclude_zero', row=number))
                continue
        if source == target:
            report.add('warning' if self_loop_policy == 'keep' else 'error', 'self_loop',
                       'Same-country cross-border record requires explicit keep policy.', number)
        records.append(dict(source=source, target=target, exposure=exposure,
                            exposure_unit='million USD', period=period,
                            source_metadata=dict(original_fields=original_rows[number - 2], source_row=number)))
    report.transformations.append(dict(operation='projection', excluded_counts=exclusions,
                                        description='Filter dimensions/period/country scope; no aggregation.'))
    report.transformations.append(dict(operation='derive_node_roster',
        description='Country codes from selected records; absent pairs remain unknown.'))
    if report.selected_rows == 0:
        report.add('error', 'empty_selection', 'No bilateral country records match this period/profile.')
    elif not records:
        report.add('error', 'empty_observed_graph', 'No observed positive edges remain; missing data is not a zero-exposure network.')
    return Dataset(list(nodes.values()), records, report, period)
