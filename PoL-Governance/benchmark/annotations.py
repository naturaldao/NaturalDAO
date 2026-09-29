"""Prepare blind pilot worksheets and compare independent review submissions."""
import argparse
import hashlib
import json
from pathlib import Path

from evaluate import ACTIONS, ISSUES, STATUSES, index_rows, read_jsonl, require, unique_list
from export_inputs import input_view

def worksheet(cases, reviewer):
    require(isinstance(reviewer, str) and bool(reviewer.strip()), 'Reviewer id required')
    return [{**row, 'annotator_id': reviewer, 'completion': 'pending',
             'status': None, 'issues': [], 'acceptable_actions': [],
             'brief_reason': '', 'policy_dispute': None} for row in input_view(cases)]

def validate_annotations(rows, expected):
    indexed = index_rows(rows)
    require(bool(indexed), 'Empty worksheet; submit pending rows instead')
    require(not (set(indexed) - set(expected)), 'Unknown annotation ids')
    reviewers = set()
    for key, row in indexed.items():
        require(set(row) == {'id', 'input', 'annotator_id', 'completion', 'status',
                            'issues', 'acceptable_actions', 'brief_reason', 'policy_dispute'},
                f'{key}: unexpected/missing worksheet fields')
        require(row['input'] == expected[key]['input'], f'{key}: input changed; use matching dataset version')
        require(isinstance(row['annotator_id'], str) and bool(row['annotator_id'].strip()), f'{key}: reviewer required')
        reviewers.add(row['annotator_id'].strip())
        require(row['completion'] in ('pending', 'complete'), f'{key}: completion')
        require(unique_list(row['issues'], ISSUES), f'{key}: issues')
        require(unique_list(row['acceptable_actions'], ACTIONS), f'{key}: actions')
        require(isinstance(row['brief_reason'], str), f'{key}: reason must be string')
        if row['completion'] == 'complete':
            require(row['status'] in STATUSES, f'{key}: complete status required')
            require(bool(row['acceptable_actions']) and bool(row['brief_reason'].strip()), f'{key}: actions/reason required')
            require(type(row['policy_dispute']) is bool, f'{key}: explicit policy_dispute required')
        else:
            require(row['status'] is None or row['status'] in STATUSES, f'{key}: draft status')
            require(row['policy_dispute'] is None or type(row['policy_dispute']) is bool, f'{key}: draft policy_dispute')
    require(len(reviewers) == 1, 'One reviewer per worksheet')
    return indexed, next(iter(reviewers))

def compare(cases, left_rows, right_rows):
    expected = {row['id']: row for row in input_view(cases)}
    left, left_id = validate_annotations(left_rows, expected)
    right, right_id = validate_annotations(right_rows, expected)
    require(left_id != right_id, 'Distinct reviewer ids required; identity is self-reported')
    paired = [key for key in expected if all(key in side and side[key]['completion'] == 'complete' for side in (left, right))]
    def fraction(count):
        return {'count': count, 'denominator': len(paired), 'rate': count / len(paired) if paired else None}
    disagreements = []
    for key in paired:
        a, b = left[key], right[key]
        flags = []
        if a['status'] != b['status']:
            flags.append('status')
        if set(a['issues']) != set(b['issues']):
            flags.append('issues')
        if set(a['acceptable_actions']) != set(b['acceptable_actions']):
            flags.append('action_set')
        if not (set(a['acceptable_actions']) & set(b['acceptable_actions'])):
            flags.append('no_shared_action')
        if a['policy_dispute'] or b['policy_dispute']:
            flags.append('policy_interpretation')
        if flags:
            disagreements.append({'id': key, 'flags': flags,
                'reviews': [{field: row[field] for field in ('annotator_id', 'status', 'issues',
                           'acceptable_actions', 'brief_reason', 'policy_dispute')} for row in (a, b)]})
    return {
        'report_kind': 'annotation_disagreement_review', 'gold_created': False,
        'reviewer_ids': [left_id, right_id], 'independence_verified': False,
        'total_cases': len(expected), 'paired_complete': len(paired),
        'coverage': len(paired) / len(expected),
        'unpaired_ids': [key for key in expected if key not in paired],
        'missing_ids': {left_id: sorted(set(expected) - set(left)), right_id: sorted(set(expected) - set(right))},
        'status_exact_agreement': fraction(sum(left[k]['status'] == right[k]['status'] for k in paired)),
        'issues_exact_agreement': fraction(sum(set(left[k]['issues']) == set(right[k]['issues']) for k in paired)),
        'action_set_exact_agreement': fraction(sum(set(left[k]['acceptable_actions']) == set(right[k]['acceptable_actions']) for k in paired)),
        'action_intersection_nonempty': fraction(sum(bool(set(left[k]['acceptable_actions']) & set(right[k]['acceptable_actions'])) for k in paired)),
        'policy_dispute_cases': [k for k in paired if left[k]['policy_dispute'] or right[k]['policy_dispute']],
        'disagreements': disagreements,
        'next': 'Independent adjudication required; agreement is not correctness or proof of independence'
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('prepare')
    init.add_argument('--reviewer', required=True)
    init.add_argument('--output', type=Path, required=True)
    diff = sub.add_parser('compare')
    diff.add_argument('--left', type=Path, required=True)
    diff.add_argument('--right', type=Path, required=True)
    for command in (init, diff):
        command.add_argument('--cases', type=Path, default=Path(__file__).with_name('pilot.jsonl'))
    args = parser.parse_args()
    try:
        cases = read_jsonl(args.cases)
        if args.command == 'prepare':
            rows = worksheet(cases, args.reviewer)
            with args.output.open('x', encoding='utf-8', newline='\n') as stream:
                for row in rows:
                    stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            print(f'Created {len(rows)} pending rows; no reference answers or completed reviews.')
        else:
            report = compare(cases, read_jsonl(args.left), read_jsonl(args.right))
            report['input_sha256'] = {name: hashlib.sha256(path.read_bytes()).hexdigest()
                                      for name, path in [('cases', args.cases), ('left', args.left), ('right', args.right)]}
            print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError) as error:
        parser.exit(2, f'Annotation error: {error}\n')

if __name__ == '__main__':
    main()
