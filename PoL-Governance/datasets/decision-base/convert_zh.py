#!/usr/bin/env python3
r"""中文来源 → decision-base 契约条目（抓取 + 转换 + 报告，仅标准库）。

配套契约：datasets/decision-base/README.md；来源清单：datasets/decision-base/sources.zh.json；
调研与准入证据：datasets/decision-base/zh-survey.md。

为什么单独一个文件
------------------
db-hf 的 fetch.py / convert.py 处理英文来源；中文来源的字段、许可与标注口径都不一样，
但**条目形状必须与英文条目完全一致**才能进同一份 items.jsonl。因此这里：
- 抓取直接复用 fetch.py（datasets-server 分页、断点续跑、revision 校验、manifest）；
- 组装直接复用 convert.py 的 build_item（id 派生 db-<slug>-<8hex>、状态去重、meta 截断、
  documented/direct 映射开关），本文件只写中文来源自己的字段解析；
- 产物默认写在仓库外 D:\pol2-raw\zh-items\items.zh.jsonl，不碰 data/items.jsonl。

四个子命令
----------
    uv run --no-project --offline python datasets/decision-base/convert_zh.py fetch --all
    uv run --no-project --offline python datasets/decision-base/convert_zh.py convert --all \
        --out D:\pol2-raw\zh-items\items.zh.jsonl
    uv run --no-project --offline python datasets/decision-base/convert_zh.py run --source cvalues-rlhf \
        --source chinese-emotion-dialogue --limit 200
    uv run --no-project --offline python datasets/decision-base/convert_zh.py merge \
        --zh D:\pol2-raw\zh-items\items.zh.jsonl --out datasets/decision-base/data/items.bilingual.jsonl

merge 把英文 items.jsonl 与中文条目合成双语底座：英文原样不动，中文按**域分层抽样**
（每域下限 1,200 → 剩余按容量比例分域 → 域内按容量比例分源 → 源内 sha256(seed+id) 顺序取），
单一来源不超过中文样本的 40%，默认目标中文占比 0.32（30% 底线 + 2 个点余量）。

硬规则
------
1. 只取 train（textdetox 的中文子集是一个语言 split，来源里单独注明）。
2. 准入来源必须在 sources.zh.json 里，且不能出现在 excluded（机器翻译、评测集、NC 许可等）。
3. 不硬塞：源字段与 taxonomy 键语义对不上时，原文进 meta.source_record，targets 留空等外部答案源。
4. lang="zh"，id 与英文条目同规则；merge 会拒绝任何跨语言 id 碰撞。
5. merge 不改写英文条目（按原顺序原样输出），只在中文侧做抽样。

测试全离线：python -m unittest discover -s datasets/decision-base -p "test_*.py"
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import convert as convert_mod          # noqa: E402  只读复用：build_item / read_rows / Context
import fetch as fetch_mod              # noqa: E402  只读复用：datasets-server 分页与 manifest

CONVERTER_NAME = "convert_zh.py"
CONVERTER_VERSION = "0.1"
DEFAULT_SOURCES = HERE / "sources.zh.json"
DEFAULT_RAW_ROOT = Path(r"D:\pol2-raw")
DEFAULT_OUT = Path(r"D:\pol2-raw\zh-items\items.zh.jsonl")
DIRECT, DOCUMENTED = convert_mod.DIRECT, convert_mod.DOCUMENTED

REQUIRED_FIELDS = ("slug", "dataset", "revision", "license", "config", "split", "domain",
                   "converter", "lang", "row_limit")
ALLOWED_LICENSES = ("apache-2.0", "mit", "cc-by-2.0", "cc-by-4.0", "cc-by-sa-4.0", "cc0-1.0",
                    "openrail++", "bsd")
#: split 白名单：中文来源里只有 textdetox 的中文子集把「中文」放在 split 上（语言即 split）
ALLOWED_SPLITS = ("train", "zh")
MAX_META_TEXT = 600

#: CValues 的 pos_type：人类标注认为【拒绝】是妥当回应（拒绝为主 / 拒绝 + 正向建议）
CVALUES_REFUSAL_TYPES = ("拒绝为主", "拒绝&正向建议")

#: 情绪标签 → taxonomy 的 emotion_primary（documented；不在表里的打旗标留空）
EMOTION_MAP = {
    "平淡語氣": "neutral", "平淡语气": "neutral", "平静": "neutral", "neutral": "neutral",
    "開心語調": "joy", "开心": "joy", "joy": "joy",
    "悲傷語調": "sadness", "伤心": "sadness", "悲伤": "sadness", "sadness": "sadness",
    "憤怒語調": "anger", "生气": "anger", "anger": "anger",
    "驚訝語調": "surprise", "驚奇語調": "surprise", "惊讶": "surprise", "surprise": "surprise",
    "恐懼語調": "fear", "fear": "fear",
    "厭惡語調": "disgust", "厌恶": "disgust", "disgust": "disgust",
    "疑問語調": "other", "confuse": "other", "其他": "other",
}

#: med-guard 的三级处置 → taxonomy 的 recommended_action（documented，原始值进 meta）
MED_GUARD_ACTION = {"放行": "allow", "观察": "review", "拦截": "block"}

#: 长者防诈骗：只收中文/粤语行
ELDER_ZH_LANGUAGES = ("mandarin", "cantonese")


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().replace(microsecond=0).isoformat()


def clip(text: str, limit: int = MAX_META_TEXT) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + " […]"


# ---------------------------------------------------------------- 来源清单

_TAXONOMY = None


def load_taxonomy():
    """taxonomy 只加载一次（convert.py 的 load_taxonomy 每次都要重新 exec 模块）。"""
    global _TAXONOMY
    if _TAXONOMY is None:
        _TAXONOMY = convert_mod.load_taxonomy()
    return _TAXONOMY


def load_sources(path: Path) -> dict:
    """读 sources.zh.json 并逐条校验；任何一条不合规就整体拒绝（不静默跳过）。"""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise SystemExit(f"读不到来源清单 {path}：{error}")
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} 不是合法 JSON：{error}")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SystemExit(f"{path}: 缺 sources 数组")
    excluded = {row.get("dataset") for row in payload.get("excluded", [])}
    seen = set()
    for source in sources:
        slug = source.get("slug")
        for field in REQUIRED_FIELDS:
            if source.get(field) in (None, ""):
                raise SystemExit(f"{path}: 来源 {slug or source} 缺字段 {field}")
        if slug in seen:
            raise SystemExit(f"{path}: slug 重复 {slug}")
        seen.add(slug)
        revision = str(source["revision"])
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
            raise SystemExit(f"{slug}: revision 必须是 40 位 commit sha（{revision!r}）")
        if source["lang"] != "zh":
            raise SystemExit(f"{slug}: 本清单只收 lang=zh 的来源（{source['lang']!r}）")
        if source["split"] not in ALLOWED_SPLITS:
            raise SystemExit(f"{slug}: split={source['split']!r} 不在 {ALLOWED_SPLITS}；只取 train")
        if str(source["license"]).lower() not in ALLOWED_LICENSES:
            raise SystemExit(f"{slug}: 许可 {source['license']!r} 不在白名单 {ALLOWED_LICENSES}")
        if source["dataset"] in excluded:
            raise SystemExit(f"{slug}: {source['dataset']} 出现在 excluded 里，不能同时准入")
        if source["converter"] not in CONVERTERS:
            raise SystemExit(f"{slug}: 未知转换器 {source['converter']!r}；可用 {sorted(CONVERTERS)}")
        if source["domain"] not in load_taxonomy().DOMAINS:
            raise SystemExit(f"{slug}: 未知覆盖域 {source['domain']!r}")
    return payload


def select_sources(payload: dict, names):
    index = {source["slug"]: source for source in payload["sources"]}
    if not names:
        return list(payload["sources"])
    missing = [name for name in names if name not in index]
    if missing:
        raise SystemExit(f"未知来源 {missing}；可用：{sorted(index)}")
    return [index[name] for name in names]


# ---------------------------------------------------------------- 组装工具

def emit_row(ctx, unit, row, *, domain, state, mapped=(), flags=(), meta_extra=None, variant=""):
    """裁剪 state、组装条目并交给 unit.emit（去重与校验都在那里）。row 是源行号。"""
    state, clip_flag = convert_mod.clip_state(state, ctx.max_state_chars)
    recorded = list(flags)
    if clip_flag:
        recorded.append(clip_flag)
    built = convert_mod.build_item(
        ctx.taxonomy, slug=unit.slug, manifest=unit.manifest, row=row, domain=domain, state=state,
        mapped=mapped, flags=recorded, meta_extra=meta_extra, question_lang=ctx.question_lang,
        mappings=ctx.mappings, variant=variant)
    item, errors = built
    # build_item 会把 converter 写成 convert.py；中文来源由本文件解析，如实改写署名。
    if isinstance(item, dict) and isinstance(item.get("meta"), dict):
        item["meta"]["converter"] = CONVERTER_NAME
        item["meta"]["converter_version"] = CONVERTER_VERSION
        item["meta"]["item_shape_from"] = convert_mod.CONVERTER_NAME
    return unit.emit((item, errors))


def answer(flag: bool) -> dict:
    return {"answer": "yes" if flag else "no"}


# ---------------------------------------------------------------- 各来源转换器

def convert_cvalues(ctx, unit):
    """Skepsun/cvalues_rlhf：中文价值观对齐（CValues-Comparison）。

    pos_type 是人工标注「妥当回应」的类型（拒绝为主 / 拒绝&正向建议），因此
    refusal_appropriate=yes 是有据可查的 documented 映射；neg_resp 与两种类型原文进 meta。
    """
    for row, payload in unit.rows:
        state = str(payload.get("prompt") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        pos_type = str(payload.get("pos_type") or "").strip()
        neg_type = str(payload.get("neg_type") or "").strip()
        mapped, flags = [], []
        if pos_type in CVALUES_REFUSAL_TYPES:
            mapped.append({"key": "refusal_appropriate", "mapping": DOCUMENTED,
                           "target": answer(True)})
            flags.append("cvalues_pos_type:" + pos_type)
        else:
            flags.append("source_target_unmapped:pos_type=" + (pos_type or "null"))
        if neg_type:
            flags.append("cvalues_neg_type:" + neg_type)
        emit_row(ctx, unit, row, domain="risk_harm", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "cvalues_refusal_preferred",
                             "pos_type": pos_type, "neg_type": neg_type,
                             "source_record": {"pos_resp": clip(payload.get("pos_resp")),
                                               "neg_resp": clip(payload.get("neg_resp"))}})


def convert_zhihu_pref(ctx, unit):
    """liyucheng/zhihu_rlhf_3k：知乎真人偏好（高赞 vs 低赞回答）。

    taxonomy 没有「哪个回答更好」的键，因此不硬塞：只作 state，回答与票数进 meta，
    targets 留空等外部答案源。
    """
    for row, payload in unit.rows:
        state = str(payload.get("prompt") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        emit_row(ctx, unit, row, domain="social_moral", state=state, mapped=[],
                 flags=["human_preference_upvotes", "source_target_unmapped:chosen_rejected"],
                 meta_extra={"domain_rule": "zhihu_human_preference",
                             "question_id": payload.get("question_id"),
                             "upvotes_chosen": payload.get("upvotes_chosen"),
                             "upvotes_rejected": payload.get("upvotes_rejected"),
                             "source_record": {"chosen": clip(payload.get("chosen")),
                                               "rejected": clip(payload.get("rejected"))}})


def convert_emotion_zh(ctx, unit):
    """Johnson8187/Chinese_Multi-Emotion_Dialogue_Dataset：8 类情绪（人工标注）。"""
    for row, payload in unit.rows:
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        label = str(payload.get("emotion") or "").strip()
        key = EMOTION_MAP.get(label)
        mapped, flags = [], []
        if key:
            mapped.append({"key": "emotion_primary", "mapping": DOCUMENTED,
                           "target": {"answer": key}})
            flags.append("emotion_map:" + label + "->" + key)
        else:
            flags.append("unmapped_emotion:" + (label or "null"))
        emit_row(ctx, unit, row, domain="human_judgment", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "chinese_emotion_dialogue", "emotion": label})


def convert_sentiment_zh(ctx, unit):
    """YiMeng-SYSU/chinese-logic-sentiment-dataset：label 0=负面 1=正面（卡面明确）。"""
    for row, payload in unit.rows:
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        mapped, flags = _binary_sentiment(payload.get("label"), source="card")
        emit_row(ctx, unit, row, domain="human_judgment", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "chinese_logic_sentiment",
                             "type": payload.get("type"), "sub_type": payload.get("sub_type"),
                             "domain": payload.get("domain"), "is_valid": payload.get("is_valid")})


def convert_sentiment_binary_zh(ctx, unit):
    """left0ver/sentiment-classification：中文商品/酒店评论，label 极性由 30 条抽样核对。"""
    for row, payload in unit.rows:
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        mapped, flags = _binary_sentiment(payload.get("label"), source="sampled")
        emit_row(ctx, unit, row, domain="human_judgment", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "baidu_review_sentiment"})


def _binary_sentiment(raw, *, source: str):
    """0/1 → negative/positive；其它取值留空。source 记录极性依据（card/sampled）。"""
    mapped, flags = [], []
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = None
    if value in (0, 1):
        mapped.append({"key": "sentiment_polarity", "mapping": DOCUMENTED,
                       "target": {"answer": "positive" if value == 1 else "negative"}})
        flags.append("label_polarity:" + source)
    else:
        flags.append("source_target_unmapped:label=" + str(raw))
    return mapped, flags


def convert_toxicity_zh(ctx, unit):
    """textdetox 中文毒性子集：text/toxic 就是 toxicity_present 的答案（direct）。"""
    for row, payload in unit.rows:
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        mapped, flags = [], []
        try:
            value = int(payload.get("toxic"))
        except (TypeError, ValueError):
            value = None
        if value in (0, 1):
            mapped.append({"key": "toxicity_present", "mapping": DIRECT,
                           "target": answer(value == 1)})
        else:
            flags.append("source_target_unmapped:toxic=" + str(payload.get("toxic")))
        emit_row(ctx, unit, row, domain="human_judgment", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "textdetox_zh_binary", "toxic": payload.get("toxic")})


def convert_elder_scam(ctx, unit):
    """vanila434/multilingual-elder-safety-msgs：只收中文/粤语行。"""
    for row, payload in unit.rows:
        language = str(payload.get("language") or "").strip()
        if language not in ELDER_ZH_LANGUAGES and not language.startswith("code_mixed"):
            unit.skip("not_chinese_row")
            continue
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        label = str(payload.get("label") or "").strip().lower()
        mapped, flags = [], []
        if label in ("scam", "safe"):
            mapped.append({"key": "contains_harm", "mapping": DOCUMENTED,
                           "target": answer(label == "scam")})
            flags.append("elder_label:" + label)
        else:
            flags.append("source_target_unmapped:label=" + (label or "null"))
        emit_row(ctx, unit, row, domain="risk_harm", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "elder_fraud_zh", "language": language,
                             "category": payload.get("category"),
                             "recommended_action": payload.get("recommended_action"),
                             "channel": payload.get("channel"),
                             "cultural_lever": payload.get("cultural_lever")})


def convert_med_guard(ctx, unit):
    """chenhaodev/med-guard-safety-synth：健康场景三级护栏判定。"""
    for row, payload in unit.rows:
        state = str(payload.get("text") or "").strip()
        if not state:
            unit.skip("empty_state")
            continue
        safety = str(payload.get("safety") or "").strip()
        action = str(payload.get("action") or "").strip()
        mapped, flags = [], []
        if safety in ("Safe", "Unsafe"):
            mapped.append({"key": "contains_harm", "mapping": DOCUMENTED,
                           "target": answer(safety == "Unsafe")})
            flags.append("med_guard_safety:" + safety)
        else:
            flags.append("source_target_unmapped:safety=" + (safety or "null"))
        if action in MED_GUARD_ACTION:
            mapped.append({"key": "recommended_action", "mapping": DOCUMENTED,
                           "target": {"answer": MED_GUARD_ACTION[action]}})
            flags.append("med_guard_action:" + action)
        else:
            flags.append("source_target_unmapped:action=" + (action or "null"))
        emit_row(ctx, unit, row, domain="risk_harm", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "med_guard_three_level", "safety": safety,
                             "action": action, "channel": payload.get("channel"),
                             "root_cause": payload.get("root_cause"),
                             "categories": payload.get("categories")})


def convert_mh_triage(ctx, unit):
    """BEncoderRT/User_Intent_Risk_Triage：中文心理危机风险分级。"""
    for row, payload in unit.rows:
        output = payload.get("output")
        if isinstance(output, str):
            try:
                output = json.loads(output)
            except (TypeError, ValueError):
                output = None
        response = (output or {}).get("response") if isinstance(output, dict) else None
        state = str(payload.get("input") or "").strip()
        if not state and isinstance(output, dict):
            turns = output.get("conversation") or []
            state = "\n".join(f"{turn.get('role')}: {turn.get('content')}"
                              for turn in turns if isinstance(turn, dict))[:ctx.max_state_chars]
        if not state:
            unit.skip("empty_state")
            continue
        risk = str((response or {}).get("risk") or "").strip().lower()
        mapped, flags = [], []
        if risk in ("high", "low"):
            mapped.append({"key": "escalation_needed", "mapping": DOCUMENTED,
                           "target": answer(risk == "high")})
            flags.append("mh_risk:" + risk)
        else:
            flags.append("source_target_unmapped:risk=" + (risk or "null"))
        emit_row(ctx, unit, row, domain="risk_harm", state=state, mapped=mapped, flags=flags,
                 meta_extra={"domain_rule": "mh_risk_triage",
                             "risk": risk,
                             "intent": (response or {}).get("intent"),
                             "strategy": (response or {}).get("strategy"),
                             "uncertainty": (response or {}).get("uncertainty")})


CONVERTERS = {
    "cvalues": convert_cvalues,
    "zhihu_pref": convert_zhihu_pref,
    "emotion_zh": convert_emotion_zh,
    "sentiment_zh": convert_sentiment_zh,
    "sentiment_binary_zh": convert_sentiment_binary_zh,
    "toxicity_zh": convert_toxicity_zh,
    "elder_scam": convert_elder_scam,
    "med_guard": convert_med_guard,
    "mh_triage": convert_mh_triage,
}


# ---------------------------------------------------------------- 子命令

def raw_dir_for(source, raw_root: Path) -> Path:
    return Path(raw_root) / source["slug"]


def cmd_fetch(args) -> int:
    payload = load_sources(args.sources)
    chosen = select_sources(payload, args.source or None)
    client = fetch_mod.Client(retries=args.retries)
    done, skipped, failed = [], [], []
    for source in chosen:
        try:
            manifest = fetch_mod.fetch_source(client, source, args.raw_root, limit=args.limit,
                                              resume=args.resume, page_size=args.page_size)
            done.append(manifest)
        except fetch_mod.SourceSkipped as error:
            print(f"跳过：{error}", file=sys.stderr)
            skipped.append({"slug": source["slug"], "reason": str(error)})
        except fetch_mod.FetchError as error:
            print(f"失败：{error}", file=sys.stderr)
            failed.append(source["slug"])
    print(json.dumps({"command": "fetch", "ok": len(done), "skipped": len(skipped),
                      "failed": failed, "rows": sum(m["rows"] for m in done)},
                     ensure_ascii=False))
    return 1 if failed else 0


def convert_source(ctx, source, raw_root: Path, limit=None):
    raw_dir = raw_dir_for(source, raw_root)
    manifest_path = raw_dir / "manifest.json"
    rows_path = raw_dir / "rows.jsonl"
    if not manifest_path.is_file() or not rows_path.is_file():
        raise fetch_mod.FetchError(f"{source['slug']}: 缺 {manifest_path} 或 {rows_path}，先跑 fetch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset") != source["dataset"] or manifest.get("config") != source["config"]:
        raise fetch_mod.FetchError(f"{source['slug']}: manifest 与 sources.zh.json 不一致，需重抓")
    rows = convert_mod.read_rows(rows_path, limit=limit)
    prepared = dict(manifest)
    prepared["_created_at"] = ctx.created_at
    prepared["_domain_rule"] = source.get("domain_rule") or source["converter"] + "_zh"
    unit = convert_mod.Unit(source["slug"], prepared, rows, ctx,
                            limit=limit, stratum_cap=float(source.get("stratum_cap", 1.0)))
    unit.rows_read = len(rows)
    CONVERTERS[source["converter"]](ctx, unit)
    report = unit.report()
    report["domain"] = source["domain"]
    report["license"] = source["license"]
    report["evidence"] = source.get("evidence")
    return unit, report


def cmd_convert(args) -> int:
    payload = load_sources(args.sources)
    chosen = select_sources(payload, args.source or None)
    taxonomy = convert_mod.load_taxonomy()
    ctx = convert_mod.Context(taxonomy, mappings=args.mappings, question_lang="zh",
                              created_at=args.created_at, log=print)
    items, reports, problems = [], [], []
    for source in chosen:
        try:
            unit, report = convert_source(ctx, source, args.raw_root, limit=args.limit)
        except fetch_mod.FetchError as error:
            print(f"失败：{error}", file=sys.stderr)
            problems.append(str(error))
            continue
        items.extend(unit.emitted)
        reports.append(report)
    item_errors = []
    for item in items:
        errors = taxonomy.item_errors(item)
        if errors:
            item_errors.append({"id": item.get("id"), "errors": errors[:3]})
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(convert_mod.jsonl_line(item))
    by_domain, by_lang, with_targets = {}, {}, 0
    for item in items:
        by_domain[item["domain"]] = by_domain.get(item["domain"], 0) + 1
        by_lang[item["lang"]] = by_lang.get(item["lang"], 0) + 1
        if item.get("targets"):
            with_targets += 1
    report = {
        "converter": CONVERTER_NAME, "converter_version": CONVERTER_VERSION,
        "created_at": ctx.created_at, "raw_root": str(args.raw_root), "out": str(args.out),
        "limit": args.limit, "mappings": args.mappings, "question_lang": "zh",
        "sources": len(reports), "items": len(items), "items_with_targets": with_targets,
        "native_target_rate": round(with_targets / len(items), 4) if items else 0.0,
        "pending_external_answers": len(items) - with_targets,
        "by_domain": by_domain, "by_lang": by_lang,
        "item_errors": len(item_errors), "item_errors_examples": item_errors[:5],
        "units": reports, "problems": problems,
    }
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(json.dumps({"command": "convert", "items": report["items"],
                      "with_targets": report["items_with_targets"],
                      "native_target_rate": report["native_target_rate"],
                      "by_domain": by_domain, "item_errors": len(item_errors),
                      "problems": len(problems)}, ensure_ascii=False))
    return 1 if (item_errors or problems) else 0


def cmd_run(args) -> int:
    code = cmd_fetch(args)
    if code != 0:
        print(json.dumps({"command": "run", "stage": "fetch", "status": "failed"},
                         ensure_ascii=False))
        return code
    return cmd_convert(args)


# ---------------------------------------------------------------- 双语合并

DEFAULT_EN_ITEMS = HERE / "data" / "items.jsonl"
DEFAULT_BI_OUT = HERE / "data" / "items.bilingual.jsonl"
DEFAULT_ZH_SHARE = 0.32          # 目标中文占比：30% 底线 + 2 个点余量
DEFAULT_SOURCE_CAP_RATIO = 0.40  # 单一来源在中文样本中的上限（README §4）
DEFAULT_DOMAIN_FLOOR = 1200      # 每个中文域的覆盖下限（README §4）
DEFAULT_SAMPLE_SEED = "pol2-bilingual-v1"


def load_items(path: Path):
    items = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def stable_order(items, seed: str):
    """确定性取样顺序：按 sha256(seed+id) 排序，避免只取文件头部。"""
    return sorted(items, key=lambda item: hashlib.sha256(
        (seed + str(item.get("id"))).encode("utf-8")).hexdigest())


def _allocate(capacities: dict, target: int) -> dict:
    """按容量比例分配 target（最大余数法），任何一项不超过其容量。"""
    capacities = {key: int(value) for key, value in capacities.items() if value > 0}
    result = {key: 0 for key in capacities}
    total_cap = sum(capacities.values())
    target = max(0, min(int(target), total_cap))
    if target == 0 or total_cap == 0:
        return result
    if target == total_cap:
        return dict(capacities)
    exact = {key: target * value / total_cap for key, value in capacities.items()}
    for key, value in exact.items():
        result[key] = min(int(value), capacities[key])
    remainder = target - sum(result.values())
    for key in sorted(exact, key=lambda k: (-(exact[k] - int(exact[k])), k)):
        if remainder <= 0:
            break
        if result[key] < capacities[key]:
            result[key] += 1
            remainder -= 1
    return result


def stratified_sample(items, target: int, *, source_cap_ratio: float = DEFAULT_SOURCE_CAP_RATIO,
                      domain_floor: int = DEFAULT_DOMAIN_FLOOR, seed: str = DEFAULT_SAMPLE_SEED):
    """中文侧按域分层抽样：域下限 → 按容量比例分域 → 域内按容量比例分源 → 源内哈希顺序取。

    返回 (选中的条目, 说明)。target 大于等于可用总量时原样返回。
    """
    by_source = {}
    for item in items:
        by_source.setdefault(item["source"]["slug"], []).append(item)
    source_cap = max(1, int(target * source_cap_ratio))
    capacity = {slug: min(len(rows), source_cap) for slug, rows in by_source.items()}
    domain_of = {slug: rows[0]["domain"] for slug, rows in by_source.items()}
    domain_capacity = {}
    for slug, cap in capacity.items():
        domain_capacity[domain_of[slug]] = domain_capacity.get(domain_of[slug], 0) + cap
    available = sum(domain_capacity.values())
    if target >= len(items) or target >= available:
        return list(items), {"mode": "keep_all", "target": target, "available": available,
                             "source_cap": source_cap, "domain_capacity": domain_capacity}
    # 先给每个域下限，再按剩余容量比例分配；预算连下限都不够时按下限等比缩小
    floors = {domain: min(domain_floor, capacity) for domain, capacity in domain_capacity.items()}
    if target < sum(floors.values()):
        domain_budget = _allocate(floors, target)
    else:
        domain_budget = dict(floors)
        remaining_capacity = {domain: domain_capacity[domain] - floors[domain]
                              for domain in domain_capacity}
        extra = _allocate(remaining_capacity, target - sum(floors.values()))
        for domain, count in extra.items():
            domain_budget[domain] = domain_budget.get(domain, 0) + count
    chosen, per_source = [], {}
    for domain, budget in sorted(domain_budget.items()):
        slugs = sorted(slug for slug in capacity if domain_of[slug] == domain)
        budgets = _allocate({slug: capacity[slug] for slug in slugs}, budget)
        for slug in slugs:
            rows = stable_order(by_source[slug], seed)[:budgets[slug]]
            per_source[slug] = {"available": len(by_source[slug]), "capacity": capacity[slug],
                                "kept": len(rows), "domain": domain}
            chosen.extend(rows)
    note = {"mode": "stratified", "target": target, "available": available,
            "source_cap": source_cap, "domain_capacity": domain_capacity,
            "domain_budget": domain_budget, "per_source": per_source,
            "source_cap_ratio": source_cap_ratio, "domain_floor": domain_floor, "seed": seed}
    return chosen, note


def summarize_items(items, taxonomy):
    by_lang, by_lang_targets, by_domain, by_domain_lang, by_source = {}, {}, {}, {}, {}
    errors = 0
    for item in items:
        lang = item.get("lang")
        by_lang[lang] = by_lang.get(lang, 0) + 1
        domain = item.get("domain")
        by_domain[domain] = by_domain.get(domain, 0) + 1
        by_domain_lang.setdefault(domain, {})
        by_domain_lang[domain][lang] = by_domain_lang[domain].get(lang, 0) + 1
        slug = (item.get("source") or {}).get("slug") or (item.get("source") or {}).get("dataset")
        by_source[slug] = by_source.get(slug, 0) + 1
        if item.get("targets"):
            by_lang_targets[lang] = by_lang_targets.get(lang, 0) + 1
        if taxonomy.item_errors(item):
            errors += 1
    total = len(items)
    return {
        "items": total,
        "by_lang": by_lang,
        "lang_share": {lang: round(count / total, 4) for lang, count in by_lang.items()} if total else {},
        "items_with_targets_by_lang": by_lang_targets,
        "native_target_rate_by_lang": {lang: round(by_lang_targets.get(lang, 0) / count, 4)
                                       for lang, count in by_lang.items()} if total else {},
        "by_domain": by_domain,
        "by_domain_lang": by_domain_lang,
        "by_source": by_source,
        "item_errors": errors,
    }


def cmd_merge(args) -> int:
    taxonomy = load_taxonomy()
    en_items = load_items(args.en)
    zh_items = load_items(args.zh)
    problems = []
    for lang, rows in (("en", en_items), ("zh", zh_items)):
        seen = set()
        for item in rows:
            item_id = item.get("id")
            if item_id in seen:
                problems.append(f"{lang}: id 重复 {item_id}")
            seen.add(item_id)
            if item.get("lang") != lang:
                problems.append(f"{lang}: lang={item.get('lang')!r} 与语言侧不符（{item_id}）")
    collisions = sorted({item["id"] for item in en_items} & {item["id"] for item in zh_items})
    if collisions:
        problems.append(f"id 跨语言碰撞 {len(collisions)} 条：{collisions[:5]}")
    if problems:
        for problem in problems[:10]:
            print(f"PROBLEM {problem}", file=sys.stderr)
        print(json.dumps({"status": "failed", "problems": problems[:10]}, ensure_ascii=False))
        return 1

    share = float(args.zh_share)
    target_zh = int(round(len(en_items) * share / (1 - share)))
    if target_zh >= len(zh_items):
        chosen, note = list(zh_items), {"mode": "keep_all", "target": target_zh,
                                        "available": len(zh_items)}
    else:
        chosen, note = stratified_sample(zh_items, target_zh,
                                         source_cap_ratio=args.source_cap_ratio,
                                         domain_floor=args.domain_floor, seed=args.seed)
    merged = list(en_items) + sorted(chosen, key=lambda item: str(item.get("id")))
    summary = summarize_items(merged, taxonomy)
    summary["en_items"] = len(en_items)
    summary["zh_available"] = len(zh_items)
    summary["zh_kept"] = len(chosen)
    summary["target_zh_share"] = share
    summary["zh_share_floor"] = 0.30
    summary["sampling"] = note
    summary["collisions"] = 0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for item in merged:
            handle.write(convert_mod.jsonl_line(item))
    summary["out"] = str(out)
    summary["out_bytes"] = out.stat().st_size
    summary["out_sha256"] = _file_sha256(out)
    summary["en_sha256"] = _file_sha256(args.en)
    summary["zh_sha256"] = _file_sha256(args.zh)
    summary["created_at"] = args.created_at or utc_now()
    if not args.no_gz:
        gz_path = Path(str(out) + ".gz")
        with out.open("rb") as source, gzip.open(gz_path, "wb", compresslevel=9) as target:
            for chunk in iter(lambda: source.read(1 << 20), b""):
                target.write(chunk)
        summary["gz"] = str(gz_path)
        summary["gz_bytes"] = gz_path.stat().st_size
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(json.dumps({"command": "merge", "items": summary["items"], "en": len(en_items),
                      "zh": len(chosen), "zh_available": len(zh_items),
                      "lang_share": summary["lang_share"],
                      "native_target_rate_by_lang": summary["native_target_rate_by_lang"],
                      "item_errors": summary["item_errors"], "mode": note["mode"],
                      "out": str(out), "gz_bytes": summary.get("gz_bytes")},
                     ensure_ascii=False))
    return 0


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target):
        target.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
        target.add_argument("--source", action="append", default=[], help="只处理指定 slug（可重复）")
        target.add_argument("--all", action="store_true", help="处理 sources.zh.json 里的全部来源")
        target.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
        target.add_argument("--limit", type=int, default=None, help="每源行数上限（小样本打通用）")

    fetch = sub.add_parser("fetch", help="抓取中文来源（datasets-server 分页，复用 fetch.py）")
    add_common(fetch)
    fetch.add_argument("--page-size", type=int, default=fetch_mod.PAGE_SIZE)
    fetch.add_argument("--resume", action="store_true")
    fetch.add_argument("--retries", type=int, default=6)
    fetch.set_defaults(func=cmd_fetch)

    convert = sub.add_parser("convert", help="把原始行转成 items（默认写仓库外）")
    add_common(convert)
    convert.add_argument("--out", type=Path, default=DEFAULT_OUT)
    convert.add_argument("--report", type=Path, default=None)
    convert.add_argument("--created-at", default=None, help="固定 created_at 便于逐字节复现")
    convert.add_argument("--mappings", choices=("all", "direct"), default="all")
    convert.set_defaults(func=cmd_convert)

    run = sub.add_parser("run", help="fetch + convert")
    add_common(run)
    run.add_argument("--page-size", type=int, default=fetch_mod.PAGE_SIZE)
    run.add_argument("--resume", action="store_true")
    run.add_argument("--retries", type=int, default=6)
    run.add_argument("--out", type=Path, default=DEFAULT_OUT)
    run.add_argument("--report", type=Path, default=None)
    run.add_argument("--created-at", default=None)
    run.add_argument("--mappings", choices=("all", "direct"), default="all")
    run.set_defaults(func=cmd_run)

    merge = sub.add_parser("merge", help="合并中英条目为双语底座（中文按域分层抽样）")
    merge.add_argument("--en", type=Path, default=DEFAULT_EN_ITEMS, help="英文 items.jsonl")
    merge.add_argument("--zh", type=Path, default=Path(r"D:\pol2-raw\zh-items\items.zh.jsonl"))
    merge.add_argument("--out", type=Path, default=DEFAULT_BI_OUT)
    merge.add_argument("--report", type=Path, default=None)
    merge.add_argument("--zh-share", type=float, default=DEFAULT_ZH_SHARE,
                       help=f"目标中文占比（默认 {DEFAULT_ZH_SHARE}；下限 0.30）")
    merge.add_argument("--source-cap-ratio", type=float, default=DEFAULT_SOURCE_CAP_RATIO)
    merge.add_argument("--domain-floor", type=int, default=DEFAULT_DOMAIN_FLOOR)
    merge.add_argument("--seed", default=DEFAULT_SAMPLE_SEED)
    merge.add_argument("--created-at", default=None)
    merge.add_argument("--no-gz", action="store_true")
    merge.set_defaults(func=cmd_merge)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "merge" and not args.all and not args.source:
        parser.error("请指定 --source <slug>（可重复）或 --all")
    if getattr(args, "page_size", 0) > fetch_mod.PAGE_SIZE:
        parser.error(f"--page-size 上限 {fetch_mod.PAGE_SIZE}（datasets-server 硬限制）")
    if getattr(args, "report", None) is None and getattr(args, "out", None):
        args.report = Path(str(args.out)).with_suffix(".report.json")
    try:
        return args.func(args)
    except (fetch_mod.FetchError, fetch_mod.SourceSkipped) as error:
        parser.exit(1, f"convert_zh: {error}\n")


if __name__ == "__main__":
    sys.exit(main())
