import json
import math
import re
from collections import Counter
from pathlib import Path


def tokenize(text):
    text = text.lower()
    tokens = re.findall(r'[a-z0-9_]{2,}', text)
    for sequence in re.findall(r'[\u3400-\u9fff]+', text):
        tokens.extend(sequence[i:i + 2] for i in range(max(0, len(sequence) - 1)))
        tokens.extend(sequence[i:i + 3] for i in range(max(0, len(sequence) - 2)))
    return tokens


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


class KnowledgePackage:
    def __init__(self, path):
        self.path = Path(path)
        self.manifest = json.loads((self.path / 'package-manifest.json').read_text(encoding='utf-8'))
        self.records = read_jsonl(self.path / 'search-records.jsonl')
        self.records_by_id = {row['record_id']: row for row in self.records}
        self.documents = {(row['source_path'], row['paragraph']): row for row in read_jsonl(self.path / 'documents.jsonl')}
        self.index = json.loads((self.path / 'retrieval-index.json').read_text(encoding='utf-8'))
        self.rules = {row['rule_id']: row for row in read_jsonl(self.path / 'knowledge' / 'rule-mapping.jsonl')}
        self.answers = read_jsonl(self.path / 'knowledge' / 'answers.jsonl')
        self.config = json.loads((self.path / 'knowledge' / 'retrieval-config.json').read_text(encoding='utf-8'))
        self.core_rules = [self.rules[rule_id] for rule_id in self.config['always_loaded_rules']]
        self.version = self.manifest['source_commit']
        self.package_id = self.manifest['package_id']
        self.ready_for_production = self.manifest.get('status') == 'production'

    def _score(self, query):
        counts = Counter(tokenize(query))
        scores = Counter()
        k1, b = 1.5, 0.75
        for token in counts:
            idf = self.index['idf'].get(token, 1.0)
            for doc_index, frequency in self.index['postings'].get(token, []):
                length = self.index['lengths'][doc_index]
                denom = frequency + k1 * (1 - b + b * length / self.index['average_length'])
                scores[doc_index] += idf * frequency * (k1 + 1) / denom
        return scores

    def search(self, query, limit=None):
        scores = self._score(query)
        limit = limit or self.config.get('top_k', 16)
        return [dict(self.records[index], score=round(score, 4)) for index, score in scores.most_common(limit)]

    def retrieve_evidence(self, query, extra_record_ids=None):
        results = self.search(query)
        if extra_record_ids:
            existing = {result['record_id'] for result in results}
            for record_id in extra_record_ids:
                if record_id in self.records_by_id and record_id not in existing:
                    results.append(dict(self.records_by_id[record_id], score=0.0, vector_hit=True))
                    existing.add(record_id)
        rule_ids = {rule['rule_id'] for rule in self.core_rules}
        for result in results:
            rule_ids.update(result.get('rule_ids', []))
        rules = [self.rules[rule_id] for rule_id in sorted(rule_ids) if rule_id in self.rules]
        citations = []
        rules_with_sources = []
        for rule in rules:
            enriched = dict(rule)
            source_texts = []
            for ref in rule['source_refs']:
                citation = dict(ref, rule_id=rule['rule_id'], rule_type=rule['kind'], applicability=rule.get('applicability', 'general'))
                if citation not in citations:
                    citations.append(citation)
                document = self.documents.get((ref['source_path'], ref['paragraph']))
                if document:
                    source_texts.append({'source_path': ref['source_path'], 'paragraph': ref['paragraph'],
                                         'text': document['text'][:2400]})
            enriched['source_texts'] = source_texts
            rules_with_sources.append(enriched)
        return {'rules': rules_with_sources, 'citations': citations, 'search_results': results}

    def find_answer(self, query):
        normalized = re.sub(r'[\s*_~`#？?。！!]+', '', query).lower()
        for answer in self.answers:
            for question in answer['questions']:
                candidate = re.sub(r'[\s*_~`#？?。！!]+', '', question).lower()
                if normalized == candidate:
                    return answer
        return None

    def rule_snapshot(self):
        return {rule_id: {'kind': rule['kind'], 'applicability': rule.get('applicability', 'general')}
                for rule_id, rule in self.rules.items()}
