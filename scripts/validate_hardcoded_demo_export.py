import os
import json
import csv
import hashlib
import sys

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def validate_demo_exports():
    base_dir = os.path.abspath('test-data/hardcoded-demo-data')
    manifest_path = os.path.join(base_dir, 'manifest.json')

    print('=' * 60)
    print('SIH APAAR PLATFORM - HARDCODED DEMO DATA EXPORT VALIDATION')
    print('=' * 60)

    if not os.path.exists(manifest_path):
        print(f'FAIL: Manifest file not found at {manifest_path}')
        return False

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    all_passed = True
    datasets = manifest.get('datasets', [])
    print(f'Found {len(datasets)} dataset definitions in manifest.\n')

    for ds in datasets:
        src_file = ds['source_file']
        cname = ds['constant_name']
        out_file = ds['output_file']
        exp_count = ds['record_count']
        exp_cols = ds['columns']
        exp_sha = ds['sha256']

        full_csv_path = os.path.join(base_dir, out_file)
        print(f'Checking {out_file} (Source: {src_file} -> {cname})...')

        # 1. Check file exists
        if not os.path.exists(full_csv_path):
            print(f'  [FAIL] Missing CSV file: {full_csv_path}')
            all_passed = False
            continue

        # 2. Check not empty
        if os.path.getsize(full_csv_path) == 0:
            print(f'  [FAIL] File is empty: {out_file}')
            all_passed = False
            continue

        # 3. Check SHA256 checksum
        actual_sha = sha256_file(full_csv_path)
        if actual_sha != exp_sha:
            print(f'  [FAIL] SHA256 mismatch for {out_file}!')
            print(f'    Expected: {exp_sha}')
            print(f'    Actual:   {actual_sha}')
            all_passed = False
        else:
            print(f'  [PASS] SHA256 matches: {actual_sha[:16]}...')

        # 4. Check CSV parsing and record count
        try:
            with open(full_csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                actual_cols = reader.fieldnames or []
                rows = list(reader)

            # Check columns
            if actual_cols != exp_cols:
                print(f'  [FAIL] Column header mismatch!')
                print(f'    Expected: {exp_cols}')
                print(f'    Actual:   {actual_cols}')
                all_passed = False
            else:
                print(f'  [PASS] Headers match: {len(actual_cols)} columns.')

            # Check row count
            if len(rows) != exp_count:
                print(f'  [FAIL] Row count mismatch!')
                print(f'    Expected: {exp_count}')
                print(f'    Actual:   {len(rows)}')
                all_passed = False
            else:
                print(f'  [PASS] Record count matches: {len(rows)} records.')

            # Check string identifier preservation
            for r in rows:
                for k, v in r.items():
                    if 'id' in k.lower() or 'ref' in k.lower() or 'code' in k.lower():
                        if v is not None and not isinstance(v, str):
                            print(f'  [FAIL] Identifier {k}={v} is not a string!')
                            all_passed = False

            # Check nested relations if any
            if 'nested_relations' in ds:
                for rel in ds['nested_relations']:
                    rel_file = rel['output_file']
                    rel_path = os.path.join(base_dir, rel_file)
                    rel_exp_count = rel['record_count']
                    rel_exp_sha = rel['sha256']
                    print(f'  Validating relation {rel["relation_name"]} in {rel_file}...')
                    if not os.path.exists(rel_path):
                        print(f'    [FAIL] Missing relation file: {rel_file}')
                        all_passed = False
                        continue
                    act_rel_sha = sha256_file(rel_path)
                    if act_rel_sha != rel_exp_sha:
                        print(f'    [FAIL] Relation SHA256 mismatch!')
                        all_passed = False
                    with open(rel_path, 'r', newline='', encoding='utf-8') as rf:
                        r_reader = csv.DictReader(rf)
                        r_rows = list(r_reader)
                    if len(r_rows) != rel_exp_count:
                        print(f'    [FAIL] Relation record count mismatch: expected {rel_exp_count}, got {len(r_rows)}')
                        all_passed = False
                    else:
                        print(f'    [PASS] Relation verified: {len(r_rows)} records, FK {rel["foreign_key"]}.')

        except Exception as e:
            print(f'  [FAIL] Error parsing CSV: {e}')
            all_passed = False

        print()

    print('-' * 60)
    # Check import fixtures as well
    fix_dir = os.path.abspath('test-data/import-fixtures')
    print('Checking import fixtures...')
    orig_csv = os.path.join(fix_dir, 'AICTE_DivD_original.csv')
    synth_csv = os.path.join(fix_dir, 'AICTE_DivD_synthetic_valid.csv')

    if os.path.exists(orig_csv):
        with open(orig_csv, 'r', newline='', encoding='utf-8') as f:
            lines = [l for l in f if l.strip()]
        print(f'  [PASS] Original fixture preserved: {orig_csv} ({len(lines)-1} data rows).')
    else:
        print(f'  [WARN] Original fixture not found: {orig_csv}')

    if os.path.exists(synth_csv):
        with open(synth_csv, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            s_rows = list(reader)
        print(f'  [PASS] Synthetic fixture available: {synth_csv} ({len(s_rows)} data rows).')
    else:
        print(f'  [WARN] Synthetic fixture not found: {synth_csv}')

    print('=' * 60)
    if all_passed:
        print('OVERALL RESULT: ALL VALIDATION CHECKS PASSED (100% INTEGRITY)')
    else:
        print('OVERALL RESULT: VALIDATION FAILED')
    print('=' * 60)
    return all_passed

if __name__ == '__main__':
    success = validate_demo_exports()
    sys.exit(0 if success else 1)
