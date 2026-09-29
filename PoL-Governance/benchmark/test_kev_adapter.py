import copy
import json
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from evaluate import validate_predictions
from kev_adapter import build_request, parse_response, run_one, validate_endpoint, validate_inputs
from test_evaluate import case

HERE = Path(__file__).parent

def answer(choice, probabilities):
    return {'type': 'choice', 'choice': choice, 'probabilities': probabilities, 'confidence': 0.5}

def response():
    return {'answers': {
        'status': answer('violating', {'conforming': 0.3333, 'violating': 0.3334, 'insufficient': 0.3333}),
        'action': answer('repair', {'allow': 0.1, 'repair': 0.6, 'block': 0.1, 'clarify': 0.1, 'review': 0.1})}}

class KevAdapterTests(unittest.TestCase):
    def setUp(self):
        self.reference = case('a', 'violating', ['repair'])
        self.row = {'id': 'a', 'input': copy.deepcopy(self.reference['input'])}

    def test_no_label_or_id_sent_to_model(self):
        payload = build_request(self.row)
        self.assertEqual(set(payload), {'model', 'state', 'questions'})
        self.assertNotIn('id', payload['state'])
        self.assertNotIn('proposal', json.dumps(payload))
        self.assertEqual(set(payload['questions']), {'status', 'action'})
        with self.assertRaises(ValueError):
            validate_inputs([self.reference])

    def test_rounding_normalized_but_not_large_error(self):
        raw = response()
        raw['answers']['status'] = answer('conforming', dict.fromkeys(('conforming', 'violating', 'insufficient'), 0.3333))
        parsed = parse_response(raw, 'a')
        self.assertAlmostEqual(sum(parsed['status_probs'].values()), 1)
        raw['answers']['status']['probabilities']['conforming'] = 0.2
        with self.assertRaises(ValueError):
            parse_response(raw, 'a')

    def test_invalid_shape_values_and_choice(self):
        for change in ('missing', 'nan', 'bool', 'contradiction'):
            raw = response()
            status = raw['answers']['status']
            if change == 'missing': del raw['answers']['action']
            if change == 'nan': status['probabilities']['conforming'] = float('nan')
            if change == 'bool': status['probabilities']['conforming'] = True
            if change == 'contradiction': status.update(choice='violating', probabilities={'conforming': 0.9, 'violating': 0.1, 'insufficient': 0})
            with self.subTest(change=change), self.assertRaises(ValueError):
                parse_response(raw, 'a')

    def test_insufficient_is_explicit_not_low_confidence(self):
        raw = response()
        raw['answers']['status']['choice'] = 'insufficient'
        raw['answers']['status']['probabilities'] = {'conforming': 0.1, 'violating': 0.1, 'insufficient': 0.8}
        self.assertEqual(parse_response(raw, 'a')['status'], 'insufficient')

    def test_failed_responses_not_fabricated(self):
        def timeout(*args): raise socket.timeout()
        for send, expected in [(timeout, 'timeout'), (lambda *args: b'not json', 'invalid')]:
            result, trace = run_one(self.row, 'kev-latest', 'unused', 1, send=send)
            self.assertEqual(result['execution_status'], expected)
            self.assertIsNone(result['status'])
            self.assertIsNone(result['action'])
            validate_predictions([result], {'a': self.reference})

    def test_no_action_clamping(self):
        raw = response()
        raw['answers']['action'] = answer('allow', {'allow': 1, 'repair': 0, 'block': 0, 'clarify': 0, 'review': 0})
        parsed = parse_response(raw, 'a')
        self.assertEqual((parsed['status'], parsed['action']), ('violating', 'allow'))

    def test_endpoint_boundary(self):
        for endpoint in ['https://example.org/v1/systemone', 'http://localhost:8009/v1/systemone',
                         'http://127.0.0.1:8009/other', 'http://user:secret@127.0.0.1/v1/systemone',
                         'http://127.0.0.1/v1/systemone?token=secret']:
            with self.assertRaises(ValueError): validate_endpoint(endpoint)
        self.assertEqual(validate_endpoint('http://[::1]:8009/v1/systemone'), 'http://[::1]:8009/v1/systemone')

    def test_real_loopback_http_and_evaluator_contract(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                data = json.dumps(response()).encode()
                self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            endpoint = f'http://127.0.0.1:{server.server_port}/v1/systemone'
            result, trace = run_one(self.row, 'kev-latest', endpoint, 2)
            validate_predictions([result], {'a': self.reference})
            self.assertEqual(result['execution_status'], 'ok')
            self.assertEqual(captured[0], build_request(self.row))
            self.assertIsNotNone(trace['response_text'])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_prepare_cli_never_makes_predictions_or_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs = Path(directory) / 'inputs.jsonl'
            inputs.write_text(json.dumps(self.row) + '\n', encoding='utf-8')
            output = Path(directory) / 'prepared'
            command = [sys.executable, str(HERE / 'kev_adapter.py'), 'prepare', '--inputs', str(inputs), '--out', str(output)]
            first = subprocess.run(command, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertFalse((output / 'predictions.jsonl').exists())
            self.assertEqual(json.loads((output / 'run.json').read_text())['state'], 'prepared')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)

if __name__ == '__main__': unittest.main()
