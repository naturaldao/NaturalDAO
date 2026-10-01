"""Validate the PoL2 ontology, judging rules and minimal-pair test matrix.

Standard library only; safe to run offline:
    python datasets/pol2/ontology/check_ontology.py

Checks (all must pass before the ontology can be cited by the pipeline):
  1. pol2-labels.v0.1.json parses and every required section exists.
  2. Every clause id is well formed, unique and every label points at a known clause.
  3. Enum keys are exactly the agreed sets (status/polarity/evidence/actions/surfaces).
  4. No duplicate ids in the shared id namespace; identifiers are lower_snake_case.
  5. issues: core groups per datasets/pol2/README.md section 4 are present.
  6. love_languages: exactly the 16 clauses PoL.2.1..PoL.2.16.
  7. review_state=pending_review entries carry a note and a pending_review record.
  8. test-matrix.md: every axis has at least one pair; each pair is two rows with an
     identical plot, one changed fact, and a different expectation.
  9. Every expectation in the matrix is a known ontology value, and every clause used
     by the matrix is a known clause.
 10. JUDGE.md covers each label and documents the four hard rules.
 11. README.md is no longer the placeholder.
 12. Anchor numbering: every clause chapter number matches anchor_audit.numbering
     (the audited upstream numbering, origin/main), and no clause uses a retired
     prefix such as EAP.5. / PoL.3.4 / ENG.6. This is what catches a paper
     renumbering that would otherwise silently invalidate every citation.
 13. Optional --source-root DIR: re-verify every anchor against an exported copy of
     the audited source text (heading number + verbatim quote). The in-repo PoL/
     tree may be an older numbering, so this check is opt-in and never ambient.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONTOLOGY_PATH = HERE / "pol2-labels.v0.1.json"
MATRIX_PATH = HERE / "test-matrix.md"
JUDGE_PATH = HERE / "JUDGE.md"
README_PATH = HERE / "README.md"

STATUS_KEYS = ("conforming", "violating", "insufficient")
POLARITY_KEYS = ("love", "hate", "neither", "unclear")
EVIDENCE_KEYS = ("sufficient", "insufficient", "contradictory")
ACTION_KEYS = ("allow", "repair", "block", "clarify", "review")
SURFACE_KEYS = ("user_input", "assistant_output", "tool_action")
ISSUE_GROUPS = ("hate2_derived", "pai_specific", "native_extension")
ISSUE_DOMAINS = ("hate2", "governance_risk")
REVIEW_STATES = ("clause_traced", "pending_review")
PENDING_KINDS = ("issue", "polarity", "evidence", "mitigation", "love_language", "clause", "action", "status", "surface")
CLAUSE_NAMESPACES = ("PoL", "EAP", "ENG")

# Canonical chapter table of the audited upstream paper (origin/main @ d030b80, 2026-10-02).
# anchor_audit in the ontology must match these constants exactly: a new upstream
# renumbering has to be acknowledged here AND in clause-remap.md, never silently.
CANONICAL_NUMBERING = {
    "0": "0. 前言.md",
    "1": "1. 爱2、恨2、爱2证明、恨2证明、富爱文明.md",
    "2": "2. 爱语.md",
    "3": "3. PoL2之冥想智慧公理.md",
    "4": "4. PoL2之伦理对齐协议.md",
    "5": "5. AI和人类文明的治理：从恨2证明到爱2证明.md",
    "6": "6. 富爱文明生产公共化协议.md",
    "7": "7. 人类公共福利的治理协议.md",
    "8": "8. 总结.md",
}
CANONICAL_CHAPTERS = {"PoL": "by_doc", "EAP": "4", "ENG": None}
CANONICAL_RETIRED = ("EAP.5.", "PoL.3.4", "PoL.3.6", "ENG.6.")
CANONICAL_AUDIT_REF = "origin/main"
CANONICAL_AUDIT_COMMIT = "d030b806c35004f8046a554d523b16ce53ead5f8"
MIN_AUDIT_COMMIT_LEN = 7
SOURCE_EXPORT_HINT = ('git show "origin/main:PoL/<文件名>" > <dir>/<文件名>')

# datasets/pol2/README.md section 4: 8 hate2-derived + 2 PAI-specific issues.
CORE_ISSUES = {
    "violence_worship": "hate2_derived",
    "exclusive_private": "hate2_derived",
    "hostile_exclusion": "hate2_derived",
    "deception_distortion": "hate2_derived",
    "dignity_denial": "hate2_derived",
    "coercion_manipulation": "hate2_derived",
    "public_erosion": "hate2_derived",
    "ecological_harm": "hate2_derived",
    "fabricated_intimacy": "pai_specific",
    "emotion_state_detection": "pai_specific",
}
REQUIRED_MITIGATIONS = (
    "safety_guardianship",  # 值守安全的恨
    "legitimate_criticism",  # 正当批评
    "legitimate_anger",  # 正当愤怒
    "refusal_and_dissent",  # 拒绝与异议
    "help_seeking_distress",  # 求救
    "repair_behavior",  # 修复行为
    "play_and_humor_boundary",  # 纯粹游戏与幽默的边界
    "consent_continues",  # 持续同意仍有效
)
# benchmark/PROTOCOL.md: 待审工程标签, not PoL formal classes.
LEGACY_LABELS = (
    "dishonesty",
    "consent_boundary",
    "coercion_manipulation",
    "dignity_equality",
    "fabricated_intimacy",
    "harm_facilitation",
    "unnecessary_restriction",
)
# Every topic the team lead asked the matrix to cover.
REQUIRED_TOPICS = (
    "持续同意", "条件与例外", "正当批评", "操控与依赖", "主体与引用",
    "否定", "反事实", "证据不足", "工具越权", "注入",
    "修复优于", "不在场", "人格平等", "爱语归属", "跨物种",
)
HARD_RULE_MARKERS = ("不得用情绪或措辞当行为性质", "温柔措辞不构成免责", "值守安全的恨")

CLAUSE_RE = re.compile(r"^(PoL|EAP|ENG)\.\d+(?:\.\d+)*$")
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
MATRIX_ACTIONS_SEP = "/"
MATRIX_LIST_SEP = ","
EMPTY_CELL = "-"

PAIR_HEADER_FIRST = "pair_id"
AXIS_HEADER_FIRST = "axis"
PAIR_EXPECTATION_COLUMNS = (
    "exp_status", "exp_polarity", "exp_issues", "exp_mitigations",
    "exp_love_languages", "exp_evidence", "exp_actions",
)


class OntologyError(ValueError):
    """Raised when the ontology, matrix or judging rules are inconsistent."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_ontology(path: Path = ONTOLOGY_PATH) -> dict:
    try:
        return json.loads(_read(path))
    except json.JSONDecodeError as error:
        raise OntologyError(f"{path.name} is not valid JSON: {error}") from error


def parse_tables(text: str):
    """Return [(header, [row dict, ...]), ...] for every markdown table."""
    tables = []
    header = None
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            if header and rows:
                tables.append((header, rows))
            header, rows = None, []
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if all(set(cell) <= set("-: ") for cell in cells if cell):
            continue  # separator row
        if header is None:
            header, rows = cells, []
        else:
            if len(cells) != len(header):
                raise OntologyError(f"table row has {len(cells)} cells, header has {len(header)}: {line[:80]}")
            rows.append(dict(zip(header, cells)))
    if header and rows:
        tables.append((header, rows))
    return tables


def parse_matrix(text: str):
    """Return (axes, pair_rows) parsed from test-matrix.md."""
    axes, pair_rows = {}, []
    for header, rows in parse_tables(text):
        if header and header[0] == AXIS_HEADER_FIRST:
            for row in rows:
                axis_id = row[AXIS_HEADER_FIRST]
                if axis_id in axes:
                    raise OntologyError(f"duplicate axis id: {axis_id}")
                axes[axis_id] = row
        elif header and header[0] == PAIR_HEADER_FIRST:
            pair_rows.extend(rows)
    return axes, pair_rows


def _split_cell(value: str, sep: str) -> list:
    value = (value or "").strip()
    if value in ("", EMPTY_CELL):
        return []
    return [part.strip() for part in value.split(sep) if part.strip()]


def _enum_keys(section) -> list:
    return [entry["key"] for entry in section]


def _ids(section) -> list:
    return [entry["id"] for entry in section]


def check_ontology(data: dict) -> dict:
    for name in ("name", "version", "schema", "status_note", "hard_rules", "source_docs",
                 "clauses", "status", "polarity", "issues", "love_languages",
                 "mitigations", "evidence", "actions", "surfaces",
                 "legacy_label_map", "pending_review"):
        if name not in data:
            raise OntologyError(f"ontology is missing top-level key: {name}")

    if len(data["hard_rules"]) < 4:
        raise OntologyError("hard_rules must state at least the four base rules")

    # 1. clauses
    clauses = data["clauses"]
    if not clauses:
        raise OntologyError("clauses must not be empty")
    doc_names = {Path(entry["doc"]).name for entry in data["source_docs"]}
    for clause_id, entry in clauses.items():
        if not CLAUSE_RE.match(clause_id):
            raise OntologyError(f"malformed clause id: {clause_id}")
        for field in ("doc", "heading", "gist", "quote"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise OntologyError(f"clause {clause_id} is missing {field}")
        if Path(entry["doc"]).name not in doc_names:
            raise OntologyError(f"clause {clause_id} cites unknown doc: {entry['doc']}")

    # 2. exact enums
    for section, expected in (("status", STATUS_KEYS), ("polarity", POLARITY_KEYS),
                              ("evidence", EVIDENCE_KEYS), ("actions", ACTION_KEYS),
                              ("surfaces", SURFACE_KEYS)):
        keys = _enum_keys(data[section])
        if sorted(keys) != sorted(expected):
            raise OntologyError(f"{section} keys {keys} != expected {list(expected)}")

    # 3. labels point at known clauses
    label_sections = ("status", "polarity", "issues", "love_languages",
                      "mitigations", "evidence", "actions", "surfaces")
    for section in label_sections:
        for entry in data[section]:
            entry_id = entry.get("key") or entry.get("id")
            if not entry_id:
                raise OntologyError(f"{section} entry without key/id: {entry}")
            if not ID_RE.match(entry_id):
                raise OntologyError(f"{section} id not lower_snake_case: {entry_id}")
            if not isinstance(entry.get("criterion"), str) or not entry["criterion"].strip():
                raise OntologyError(f"{section}.{entry_id} is missing a one-line criterion")
            clause = entry.get("clause")
            if clause not in clauses:
                raise OntologyError(f"{section}.{entry_id} cites unknown clause: {clause!r}")
            for extra in entry.get("clauses", []):
                if extra not in clauses:
                    raise OntologyError(f"{section}.{entry_id} cites unknown clause: {extra!r}")
            state = entry.get("review_state", "clause_traced")
            if state not in REVIEW_STATES:
                raise OntologyError(f"{section}.{entry_id} has bad review_state: {state}")

    # 4. unique ids inside every enumeration; the three open lists stay disjoint.
    #    status=insufficient and evidence=insufficient are different fields by contract.
    for section in label_sections:
        seen = set()
        for entry in data[section]:
            entry_id = entry.get("key") or entry.get("id")
            if entry_id in seen:
                raise OntologyError(f"duplicate id {entry_id!r} in {section}")
            seen.add(entry_id)
    open_lists = {"issues": _ids(data["issues"]), "love_languages": _ids(data["love_languages"]),
                  "mitigations": _ids(data["mitigations"])}
    names = list(open_lists)
    for i, left in enumerate(names):
        for right in names[i + 1:]:
            shared = set(open_lists[left]) & set(open_lists[right])
            if shared:
                raise OntologyError(f"ids shared by {left} and {right}: {sorted(shared)}")

    # 5. issues
    issue_ids = set()
    for issue in data["issues"]:
        if issue["group"] not in ISSUE_GROUPS:
            raise OntologyError(f"issue {issue['id']} has bad group: {issue['group']}")
        if issue["domain"] not in ISSUE_DOMAINS:
            raise OntologyError(f"issue {issue['id']} has bad domain: {issue['domain']}")
        if issue["id"] in issue_ids:
            raise OntologyError(f"duplicate issue id: {issue['id']}")
        issue_ids.add(issue["id"])
    for issue_id, group in CORE_ISSUES.items():
        matched = [i for i in data["issues"] if i["id"] == issue_id]
        if not matched:
            raise OntologyError(f"core issue missing from ontology: {issue_id}")
        if matched[0]["group"] != group:
            raise OntologyError(f"core issue {issue_id} must stay in group {group}")

    # 6. love languages cover PoL.2.1..PoL.2.16 exactly
    love = data["love_languages"]
    if len(love) != 16:
        raise OntologyError(f"love_languages must have 16 entries, found {len(love)}")
    expected_love = {f"PoL.2.{i}" for i in range(1, 17)}
    got_love = {entry["clause"] for entry in love}
    if got_love != expected_love:
        raise OntologyError(f"love_languages clauses {sorted(got_love)} != {sorted(expected_love)}")

    # 7. mitigations
    mitigation_ids = {entry["id"] for entry in data["mitigations"]}
    missing = [mid for mid in REQUIRED_MITIGATIONS if mid not in mitigation_ids]
    if missing:
        raise OntologyError(f"required mitigations missing: {missing}")
    for entry in data["mitigations"]:
        if not isinstance(entry.get("effect"), str) or not entry["effect"].strip():
            raise OntologyError(f"mitigation {entry['id']} is missing effect")

    # 8. pending review bookkeeping
    pending = data["pending_review"]
    if not pending:
        raise OntologyError("pending_review must list the unsettled questions")
    pending_kinds = set()
    pending_ids = set()
    for item in pending:
        for field in ("id", "kind", "question", "why"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise OntologyError(f"pending_review item missing {field}: {item}")
        if item["kind"] not in PENDING_KINDS:
            raise OntologyError(f"pending_review item has bad kind: {item['kind']}")
        if item["id"] in pending_ids:
            raise OntologyError(f"duplicate pending_review id: {item['id']}")
        pending_ids.add(item["id"])
        pending_kinds.add(item["kind"])
        clause = item.get("clause")
        if clause is not None and clause not in clauses:
            raise OntologyError(f"pending_review {item['id']} cites unknown clause: {clause!r}")
    section_kind = {"polarity": "polarity", "evidence": "evidence", "issues": "issue",
                    "mitigations": "mitigation", "love_languages": "love_language",
                    "actions": "action", "status": "status", "surfaces": "surface"}
    for section in label_sections:
        for entry in data[section]:
            if entry.get("review_state") != "pending_review":
                continue
            entry_id = entry.get("key") or entry.get("id")
            if not entry.get("note"):
                raise OntologyError(f"{section}.{entry_id} is pending_review but has no note")
            kind = section_kind.get(section, section)
            if kind not in pending_kinds:
                raise OntologyError(f"{section}.{entry_id} is pending_review with no pending_review record")

    # 9. legacy engineering labels
    legacy = {k: v for k, v in data["legacy_label_map"].items() if k != "note"}
    if sorted(legacy) != sorted(LEGACY_LABELS):
        raise OntologyError(f"legacy_label_map keys {sorted(legacy)} != {list(LEGACY_LABELS)}")
    for key, mapping in legacy.items():
        targets = mapping.get("native_issues")
        if not isinstance(targets, list) or not targets:
            raise OntologyError(f"legacy {key} must map to at least one native issue")
        for target in targets:
            if target not in issue_ids:
                raise OntologyError(f"legacy {key} maps to unknown issue: {target}")

    # 10. anchor numbering must match the audited upstream numbering
    numbering_report = check_numbering(data)

    return {"clauses": len(clauses), "issues": len(data["issues"]),
            "core_issues": len(CORE_ISSUES), "love_languages": len(love),
            "mitigations": len(data["mitigations"]), "pending_review": len(pending),
            "source_docs": len(doc_names), **numbering_report}


def check_numbering(data: dict) -> dict:
    """Anchor chapter numbers must match the audited upstream numbering.

    This is the guard against a paper renumbering silently invalidating citations:
    anchor_audit records the audited ref/commit, the chapter table, the retired
    prefixes, and the old->new map; every clause id is checked against it.
    """
    audit = data.get("anchor_audit")
    if not isinstance(audit, dict):
        raise OntologyError("anchor_audit is missing: clause anchors cannot be audited")
    for field in ("audited_ref", "audited_commit", "audited_at", "method", "numbering",
                  "unnumbered_docs", "namespace_chapters", "retired_clause_prefixes",
                  "renumbering"):
        if field not in audit:
            raise OntologyError(f"anchor_audit is missing {field}")
    if len(str(audit["audited_commit"])) < MIN_AUDIT_COMMIT_LEN:
        raise OntologyError("anchor_audit.audited_commit is too short to be a commit id")

    numbering = audit["numbering"]
    if not isinstance(numbering, dict) or not numbering:
        raise OntologyError("anchor_audit.numbering must map chapter numbers to file names")
    by_doc = {}
    for chapter, doc in numbering.items():
        if not str(chapter).isdigit():
            raise OntologyError(f"anchor_audit.numbering key must be a chapter number: {chapter!r}")
        name = Path(str(doc)).name
        if name in by_doc:
            raise OntologyError(f"anchor_audit.numbering lists {name} twice")
        by_doc[name] = int(chapter)
    unnumbered = {Path(str(doc)).name for doc in audit["unnumbered_docs"]}
    if not unnumbered:
        raise OntologyError("anchor_audit.unnumbered_docs must list the out-of-series sources")
    both = sorted(set(by_doc) & unnumbered)
    if both:
        raise OntologyError(f"docs listed as both numbered and unnumbered: {both}")

    retired = tuple(str(prefix) for prefix in audit["retired_clause_prefixes"])
    if not retired:
        raise OntologyError("anchor_audit.retired_clause_prefixes must record the old numbering")
    namespace_chapters = audit["namespace_chapters"]
    for namespace in namespace_chapters:
        if namespace not in CLAUSE_NAMESPACES:
            raise OntologyError(f"anchor_audit.namespace_chapters has unknown namespace: {namespace}")

    # the ontology's audit block and this module's canonical constants must agree
    declared_numbering = {str(key): Path(str(value)).name for key, value in numbering.items()}
    if declared_numbering != CANONICAL_NUMBERING:
        raise OntologyError("anchor_audit.numbering differs from the canonical numbering table")
    if dict(namespace_chapters) != CANONICAL_CHAPTERS:
        raise OntologyError("anchor_audit.namespace_chapters differs from the canonical table")
    if retired != CANONICAL_RETIRED:
        raise OntologyError("anchor_audit.retired_clause_prefixes differs from the canonical table")
    if (str(audit["audited_ref"]) != CANONICAL_AUDIT_REF
            or str(audit["audited_commit"]) != CANONICAL_AUDIT_COMMIT):
        raise OntologyError("anchor_audit is not the audited revision this checker targets; "
                            "re-audit, then update clause-remap.md and the canonical constants")

    # numbering covers the whole book; source_docs only lists the docs we cite,
    # so the required direction is: every cited doc must appear in the audit.
    for name in sorted({Path(entry["doc"]).name for entry in data["source_docs"]}):
        if name not in by_doc and name not in unnumbered:
            raise OntologyError(f"source_docs lists a doc outside anchor_audit: {name}")

    numbered = 0
    for clause_id, entry in data["clauses"].items():
        for prefix in retired:
            if clause_id.startswith(prefix):
                raise OntologyError(f"clause {clause_id} still uses the retired numbering {prefix!r}")
        parts = clause_id.split(".")
        namespace = parts[0]
        if namespace not in CLAUSE_NAMESPACES:
            raise OntologyError(f"clause {clause_id} has unknown namespace")
        chapter = int(parts[1])
        doc = Path(entry["doc"]).name
        fixed = namespace_chapters.get(namespace)
        if str(fixed) == "by_doc":  # PoL.* takes its chapter from the cited document
            fixed = None
        if fixed is not None and str(chapter) != str(fixed):
            raise OntologyError(
                f"clause {clause_id} must live in chapter {fixed} of the audited numbering")
        if doc in unnumbered:
            if fixed is not None:
                raise OntologyError(f"clause {clause_id} maps {namespace} to an unnumbered doc")
            if chapter < 1:
                raise OntologyError(f"clause {clause_id} needs a positive doc-relative number")
            continue
        if doc not in by_doc:
            raise OntologyError(f"clause {clause_id} cites a doc outside anchor_audit.numbering: {doc}")
        if by_doc[doc] != chapter:
            raise OntologyError(
                f"clause {clause_id} cites {doc} (chapter {by_doc[doc]}) but its id says chapter {chapter}")
        numbered += 1

    for old, new in audit["renumbering"].items():
        if not any(prefix.startswith(str(old)) for prefix in retired):
            raise OntologyError(f"anchor_audit.renumbering source {old!r} is not a retired prefix")
        if not any(cid == str(new) or cid.startswith(str(new) + ".") for cid in data["clauses"]):
            raise OntologyError(f"anchor_audit.renumbering target {new!r} matches no current clause")

    return {"numbering_chapters": len(by_doc), "unnumbered_docs": len(unnumbered),
            "retired_prefixes": len(retired), "anchors_numbered": numbered}


def _normalise(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def check_source_alignment(data: dict, source_root) -> dict:
    """Re-verify every anchor against an exported copy of the audited source text.

    Export first, for example (PowerShell, one file at a time):
        git show "origin/main:PoL/4. PoL2之伦理对齐协议.md" > <dir>/"4. PoL2之伦理对齐协议.md"
    Every clause must then find (a) a heading whose number equals its own section
    number, and (b) its verbatim quote, in the exported file.
    """
    root = Path(source_root)
    if not root.is_dir():
        raise OntologyError(f"--source-root is not a directory: {root}")
    audit = data["anchor_audit"]
    unnumbered = {Path(str(doc)).name for doc in audit["unnumbered_docs"]}
    verified = 0
    quotes = 0
    for clause_id, entry in data["clauses"].items():
        doc = Path(entry["doc"]).name
        path = root / doc
        if not path.is_file():
            raise OntologyError(f"{clause_id}: source file not exported: {path}  ({SOURCE_EXPORT_HINT})")
        raw = _read_source(path)
        text = _normalise(raw)
        verified += 1
        if doc not in unnumbered:
            section = clause_id.split(".", 1)[1]
            pattern = re.compile(r"^#{1,6}\s*" + re.escape(section) + r"(?!\.?\d)", re.M)
            if not pattern.search(raw):
                raise OntologyError(f"{clause_id}: no heading '{section}' in {doc}")
        quote = _normalise(entry["quote"])
        if quote and quote not in text:
            raise OntologyError(f"{clause_id}: quote not found in {doc}: {entry['quote'][:48]}...")
        quotes += 1
    return {"source_root": str(root), "anchors_verified": verified, "quotes_verified": quotes}


def check_matrix(data: dict, matrix_text: str, require_topics: bool = True) -> dict:
    axes, pair_rows = parse_matrix(matrix_text)
    if not axes:
        raise OntologyError("test-matrix.md has no axis table")
    if not pair_rows:
        raise OntologyError("test-matrix.md has no pair rows")

    clause_ids = set(data["clauses"])
    issue_ids = {entry["id"] for entry in data["issues"]}
    mitigation_ids = {entry["id"] for entry in data["mitigations"]}
    love_ids = {entry["id"] for entry in data["love_languages"]}

    if require_topics:
        topics = " ".join(row.get("主题（必覆盖）", "") for row in axes.values())
        missing = [topic for topic in REQUIRED_TOPICS if topic not in topics]
        if missing:
            raise OntologyError(f"test-matrix axis table does not cover topics: {missing}")

    for axis_id, axis_row in axes.items():
        for clause in _split_cell(axis_row.get("clause", ""), MATRIX_ACTIONS_SEP):
            if clause not in clause_ids:
                raise OntologyError(f"axis {axis_id} cites unknown clause: {clause}")

    grouped = {}
    seen_pairs = set()
    for row in pair_rows:
        pair_id = row[PAIR_HEADER_FIRST]
        if pair_id in seen_pairs:
            raise OntologyError(f"duplicate pair_id in matrix: {pair_id}")
        seen_pairs.add(pair_id)
        match = re.match(r"^(AX-\d{2})-p(\d{2})$", pair_id)
        if not match:
            raise OntologyError(f"pair_id must look like AX-01-p01: {pair_id}")
        axis_id = match.group(1)
        if axis_id not in axes:
            raise OntologyError(f"pair {pair_id} references unknown axis {axis_id}")
        for column in ("scenario", "plot", "variant", "changed_fact") + PAIR_EXPECTATION_COLUMNS + ("clause",):
            if not row.get(column):
                raise OntologyError(f"pair {pair_id} is missing column {column}")
        if row["exp_status"] not in STATUS_KEYS:
            raise OntologyError(f"{pair_id}: unknown status {row['exp_status']}")
        if row["exp_polarity"] not in POLARITY_KEYS:
            raise OntologyError(f"{pair_id}: unknown polarity {row['exp_polarity']}")
        if row["exp_evidence"] not in EVIDENCE_KEYS:
            raise OntologyError(f"{pair_id}: unknown evidence {row['exp_evidence']}")
        for action in _split_cell(row["exp_actions"], MATRIX_ACTIONS_SEP):
            if action not in ACTION_KEYS:
                raise OntologyError(f"{pair_id}: unknown action {action}")
        for issue in _split_cell(row["exp_issues"], MATRIX_LIST_SEP):
            if issue not in issue_ids:
                raise OntologyError(f"{pair_id}: unknown issue {issue}")
        for mitigation in _split_cell(row["exp_mitigations"], MATRIX_LIST_SEP):
            if mitigation not in mitigation_ids:
                raise OntologyError(f"{pair_id}: unknown mitigation {mitigation}")
        for love in _split_cell(row["exp_love_languages"], MATRIX_LIST_SEP):
            if love not in love_ids:
                raise OntologyError(f"{pair_id}: unknown love language {love}")
        for clause in _split_cell(row["clause"], MATRIX_ACTIONS_SEP):
            if clause not in clause_ids:
                raise OntologyError(f"{pair_id}: unknown clause {clause}")
        grouped.setdefault((axis_id, row["scenario"]), []).append((pair_id, row))

    for axis_id in axes:
        axis_pairs = [key for key in grouped if key[0] == axis_id]
        if not axis_pairs:
            raise OntologyError(f"axis {axis_id} has no minimal pair")

    for (axis_id, scenario), rows in grouped.items():
        if len(rows) != 2:
            raise OntologyError(f"scenario {scenario} on {axis_id} must have exactly 2 rows, has {len(rows)}")
        (first_id, first), (second_id, second) = rows
        if first["plot"] != second["plot"]:
            raise OntologyError(f"{first_id}/{second_id}: plot differs, not a minimal pair")
        if first["variant"] == second["variant"]:
            raise OntologyError(f"{first_id}/{second_id}: variant labels must differ")
        if first["changed_fact"] == second["changed_fact"]:
            raise OntologyError(f"{first_id}/{second_id}: changed_fact must differ")
        if all(first[column] == second[column] for column in PAIR_EXPECTATION_COLUMNS):
            raise OntologyError(f"{first_id}/{second_id}: pair changes no expectation")

    return {"axes": len(axes), "pairs": len(grouped), "pair_rows": len(pair_rows)}


def check_docs(judge_text: str, readme_text: str, data: dict) -> dict:
    if "待填充" in readme_text or "占位符" in readme_text:
        raise OntologyError("README.md is still the placeholder")
    for marker in HARD_RULE_MARKERS:
        if marker not in judge_text:
            raise OntologyError(f"JUDGE.md does not state the hard rule: {marker}")
    for phrase in ("正例", "反例", "边界例"):
        if phrase not in judge_text:
            raise OntologyError(f"JUDGE.md does not give {phrase}")
    for issue in data["issues"]:
        if issue["id"] not in judge_text:
            raise OntologyError(f"JUDGE.md does not cover issue {issue['id']}")
    for mitigation in data["mitigations"]:
        if mitigation["id"] not in judge_text:
            raise OntologyError(f"JUDGE.md does not cover mitigation {mitigation['id']}")
    for love in data["love_languages"]:
        if love["zh"] not in judge_text:
            raise OntologyError(f"JUDGE.md does not cover love language {love['zh']}")
    return {"judge_chars": len(judge_text)}


def check(require_topics: bool = True, source_root=None) -> dict:
    data = load_ontology()
    report = {"status": "pass", "schema": data["schema"], "version": data["version"]}
    report.update(check_ontology(data))
    report.update(check_matrix(data, _read(MATRIX_PATH), require_topics=require_topics))
    report.update(check_docs(_read(JUDGE_PATH), _read(README_PATH), data))
    if source_root is None:
        report["source_alignment"] = "skipped (pass --source-root <exported PoL dir>)"
    else:
        report.update(check_source_alignment(data, source_root))
    return report


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:  # keep Chinese report text readable on cp936 consoles
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    skip_topics = "--skip-topic-check" in argv
    source_root = None
    if "--source-root" in argv:
        index = argv.index("--source-root")
        if index + 1 >= len(argv):
            print("Check failed: --source-root needs a directory argument", file=sys.stderr)
            return 1
        source_root = argv[index + 1]
    try:
        report = check(require_topics=not skip_topics, source_root=source_root)
    except (OntologyError, OSError) as error:
        print(f"Check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
