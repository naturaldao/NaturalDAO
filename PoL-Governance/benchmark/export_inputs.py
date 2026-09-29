"""Export an allowlisted input view without reference/provenance leakage."""
import argparse
import json
from pathlib import Path
from evaluate import read_jsonl, validate_cases

def input_view(rows):
    cases = validate_cases(rows)
    return [{'id': key, 'input': {field: row['input'][field]
             for field in ('surface', 'context', 'target', 'policy')}} for key, row in cases.items()]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=Path(__file__).with_name('pilot.jsonl'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        data = input_view(read_jsonl(args.cases))
        # Exclusive creation preserves existing outputs and the source file.
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            for row in data:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
    except (ValueError, OSError) as error:
        parser.exit(2, f'Export error: {error}\n')
    print(f'Exported {len(data)} public-pilot inputs; no proposal labels.')

if __name__ == '__main__':
    main()
