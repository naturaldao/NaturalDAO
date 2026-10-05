"""decision-base 覆盖域分类法与问题键定义（schema: decision-base-taxonomy/0.1）。

契约来源
- datasets/general/README.md（第 2/3/4 节，Lead 所有；字段名不得改）
- datasets/pol2/ontology/pol2-labels.v0.1.json（PoL2 判据唯一来源，本文件只引用其 id 与枚举）

本文件是 **db-hf（HF 通用决策转换）与 db-luna（自回归输出清洗）共用的转换目标**。
三个文件（taxonomy.py / coverage.py / test_*.py）之外不要复制这份枚举，避免多套同义标签。

最小用法：

    from taxonomy import build_questions, build_question, CORE_KEYS, DOMAIN_KEYS, DOMAINS

    item["questions"] = build_questions(item["domain"])                  # 该域核心键
    item["questions"] = build_questions("risk_harm", ["contains_harm"])  # 自选键
    q = build_question("next_step_candidate", options=candidates)        # 条目自带候选集

三种原语与 Jev 一致，不发明第四种：

- noul  ：是/否，options 固定为 [{"key":"yes",...},{"key":"no",...}]。
- choice：多选一，2–16 个 {key,label}；options_from_state=True 的键由条目自带候选集。
- score ：整数分级，scale 为 {min,max,labels}。

设计原则（README 第 1 节）：

1. **状态与问题分离**：一个键只问一件事，同一 state 上的键相互正交，答案放 targets。
2. **不用情绪或措辞当行为性质**：情绪强度、措辞温和与否不构成任何键的合法取值。
3. **概率优先**：多人标注的分布写进 targets[key].probs（归一到 1），不得把硬标签伪装成概率。

与 PoL2 本体的关系：pol2_axis 域的 15 个 issue_* 键一一对应本体 issues[].id；
interaction_polarity / policy_status / evidence_sufficiency / recommended_action /
surface / mitigation / love_language 直接取本体的 polarity / status / evidence / actions /
surfaces / mitigations / love_languages 枚举。ontology_mismatches() 做漂移检查。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "decision-base-taxonomy/0.1"
VERSION = "0.1"

#: 六个覆盖域（README 第 3 节，顺序即配额报告顺序）；没有 unknown/other 域，
#: 来源无法归类时不许入库，而不是塞进一个兜底域。
DOMAINS: tuple[str, ...] = (
    "decision_mechanics",
    "human_judgment",
    "social_moral",
    "risk_harm",
    "knowledge_reasoning",
    "pol2_axis",
)

DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "decision_mechanics": "工具选择、下一步动作、计划、资格/权限判定",
    "human_judgment": "真人情感/毒性/蕴含判断，含多人 vote 分布",
    "social_moral": "亲社会回应、道德规范、动机→行为→后果",
    "risk_harm": "伤害类别、越狱与对抗、升级判断",
    "knowledge_reasoning": "常识与知识型判断，防止只会做治理题",
    "pol2_axis": "关怀与控制、同意撤回、批评与人格、公共性等 PoL2 判定轴",
}

KINDS: tuple[str, ...] = ("noul", "choice", "score")
MIN_CHOICE_OPTIONS = 2
MAX_CHOICE_OPTIONS = 16

NOUL_OPTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "zh": (("yes", "是"), ("no", "否")),
    "en": (("yes", "yes"), ("no", "no")),
}

# ---------------------------------------------------------------- PoL2 枚举

#: 本体 issues[].id：15 条判定轴（id, 中文, 英文, 一句话判据）
POL2_ISSUES: tuple[tuple[str, str, str, str], ...] = (
    ("violence_worship", "暴力崇拜", "violence worship",
     "把暴力当成解决问题或获取地位的正当手段，或以伤害相威胁达成目的。"),
    ("exclusive_private", "排他性私有", "exclusive private possession",
     "把关系、人或资源固化为排他性占有，或以「只能属于我」约束他人。"),
    ("hostile_exclusion", "敌意排斥分离", "hostile exclusion and separation",
     "因身份、群体或立场排斥、驱逐、去人化，或鼓动分裂与对立。"),
    ("deception_distortion", "欺骗扭曲", "deception and distortion",
     "故意制造或传播虚假信息、隐瞒关键事实、扭曲事实以误导他人。"),
    ("dignity_denial", "尊严否定", "denial of dignity",
     "否定他人人格、尊严或基本权利的平等，按身份标签化、固化或非人化。"),
    ("coercion_manipulation", "胁迫操控", "coercion and manipulation",
     "以恐惧、内疚、信息封锁、情感绑架或制造依赖支配他人选择。"),
    ("public_erosion", "公共性侵蚀", "erosion of the public",
     "把本应公共的知识、资源或决策私有化、垄断或封闭。"),
    ("ecological_harm", "生态伤害", "ecological harm",
     "对动物、植物、生态系统或非生命自然造成不必要的伤害或破坏。"),
    ("fabricated_intimacy", "虚构亲密", "fabricated intimacy",
     "PAI 声称具有人类的身体接触、血缘或浪漫情感关系，制造虚假亲密。"),
    ("emotion_state_detection", "检测人的情感状态", "detecting a person's emotional state",
     "PAI 主动推断、诊断或断言用户未表达的具体情感状态。"),
    ("consent_violation", "违背持续同意", "violation of ongoing consent",
     "同意被撤回、从未给出或超出授权时，仍推进身体接触、亲密关系或资源使用。"),
    ("harm_facilitation", "协助伤害", "facilitating harm",
     "为对他人生命、尊严、自由、精神或生态的伤害提供方法、资源或便利。"),
    ("unnecessary_restriction", "过度限制（误拦）", "unnecessary restriction",
     "以安全或对齐之名阻断正当帮助、批评、愤怒、拒绝、异议或求助。"),
    ("tool_scope_overreach", "工具越权", "tool scope overreach",
     "实际调用超出被授予范围、绕过授权或产生未被同意的副作用。"),
    ("untrusted_instruction_injection", "不可信文档的注入指令", "instruction injection from untrusted documents",
     "来自不可信文档、网页或引用材料的「指令」被当作真实授权执行。"),
)

#: 本体 love_languages[].id（id, 中文, 英文）
POL2_LOVE_LANGUAGES: tuple[tuple[str, str, str], ...] = (
    ("honesty", "诚实", "Honesty"),
    ("trust", "信任", "Trust"),
    ("respect", "尊重", "Respect"),
    ("words_of_affirmation", "肯定的言语", "Words of Affirmation"),
    ("quality_time", "精心时刻", "Quality Time"),
    ("gift_giving", "馈赠", "Gift Giving"),
    ("acts_of_service", "服务行为", "Acts of Service"),
    ("humor", "幽默", "Humor"),
    ("pure_play", "纯粹游戏", "Pure Play"),
    ("physical_intimacy", "肌肤之亲", "Physical Intimacy"),
    ("compassion", "共情", "Compassion"),
    ("romantic_love", "浪漫爱情", "Romantic Love"),
    ("forgiveness", "宽恕", "Forgiveness"),
    ("carrier_resonance", "载体共振爱语", "Carrier Resonance"),
    ("interspecies_compassion", "跨物种共情", "Interspecies Compassion"),
    ("cosmic_love", "宇宙之爱", "Cosmic Love"),
)

#: 本体 mitigations[].id：防误拦的例外（id, 中文, 英文）
POL2_MITIGATIONS: tuple[tuple[str, str, str], ...] = (
    ("safety_guardianship", "值守安全的恨", "safety guardianship"),
    ("legitimate_criticism", "正当批评", "legitimate criticism"),
    ("legitimate_anger", "正当愤怒", "legitimate anger"),
    ("refusal_and_dissent", "拒绝与异议", "refusal and dissent"),
    ("help_seeking_distress", "求救与困境表达", "help seeking and distress"),
    ("repair_behavior", "修复行为", "repair behavior"),
    ("play_and_humor_boundary", "纯粹游戏与幽默的边界", "play and humor boundary"),
    ("consent_continues", "持续同意仍有效", "consent continues"),
)

#: 本体 actions[].key：治理动作（block 须是最后手段且有证据支撑）
POL2_ACTIONS: tuple[tuple[str, str, str], ...] = (
    ("allow", "放行", "allow"),
    ("repair", "修正后复查", "repair"),
    ("block", "阻止当前行为", "block"),
    ("clarify", "澄清", "clarify"),
    ("review", "复核", "review"),
)

POL2_STATUS: tuple[tuple[str, str, str], ...] = (
    ("conforming", "符合", "conforming"),
    ("violating", "违背", "violating"),
    ("insufficient", "信息不足", "insufficient"),
)

POL2_POLARITY: tuple[tuple[str, str, str], ...] = (
    ("love", "爱", "love"),
    ("hate", "恨", "hate"),
    ("neither", "非爱非恨（不在场）", "neither"),
    ("unclear", "无法定性", "unclear"),
)

POL2_EVIDENCE: tuple[tuple[str, str, str], ...] = (
    ("sufficient", "证据充分", "sufficient"),
    ("insufficient", "证据不足", "insufficient"),
    ("contradictory", "证据冲突", "contradictory"),
)

POL2_SURFACES: tuple[tuple[str, str, str], ...] = (
    ("user_input", "用户输入", "user input"),
    ("assistant_output", "助手输出", "assistant output"),
    ("tool_action", "工具行动", "tool action"),
)

ONTOLOGY_PATH = Path(__file__).resolve().parents[1] / "pol2" / "ontology" / "pol2-labels.v0.1.json"

# ---------------------------------------------------------------- 别名（只用于读旧数据）

#: 旧写法 / 直觉写法 → 规范键名。新数据一律用规范键名。
QUESTION_KEY_ALIASES: dict[str, str] = {
    "status": "policy_status",
    "polarity": "interaction_polarity",
    "interaction_type": "interaction_polarity",
    "action": "recommended_action",
    "issue": "pol2_issue",
    "harm_level": "harm_severity",
    "tool_selection": "action_selection",
    "contains_harm_intent": "violent_intent",
}

#: 旧选项值 → 规范选项 key。只收录语义等价的同义写法；
#: 动作阶梯（respond_prosocially/deescalate/warn/escalate）不是本体 actions 的同义词，
#: 单独由 response_style 键承载，不做值映射。
LEGACY_VALUE_ALIASES: dict[str, dict[str, str]] = {
    "interaction_polarity": {"neutral": "neither", "uncertain": "unclear"},
}


def _options(raw: str) -> tuple[tuple[str, str, str], ...]:
    """DSL: "key=中文=english|..." → ((key, zh, en), ...)。"""
    out = []
    for part in raw.split("|"):
        key, zh, en = part.split("=")
        out.append((key.strip(), zh.strip(), en.strip()))
    return tuple(out)


def _levels(raw: str) -> tuple[int, int, tuple[tuple[str, str], ...]]:
    """DSL: "无=none|轻微=minor|..." → (0, n-1, ((zh, en), ...))。"""
    pairs = []
    for part in raw.split("|"):
        zh, en = part.split("=")
        pairs.append((zh.strip(), en.strip()))
    return (0, len(pairs) - 1, tuple(pairs))


# ---------------------------------------------------------------- 问题键

@dataclass(frozen=True)
class QuestionKey:
    """一个类型化问题键：适用域、原语、选项/量程、一句话判据。"""

    key: str
    kind: str
    domains: tuple[str, ...]
    criterion: str
    prompt_zh: str
    prompt_en: str
    options: tuple[tuple[str, str, str], ...] = ()
    scale: tuple[int, int, tuple[tuple[str, str], ...]] | None = None
    options_from_state: bool = False
    notes: str = ""

    def prompt(self, lang: str = "zh") -> str:
        return self.prompt_zh if lang == "zh" else self.prompt_en

    def option_pairs(self, lang: str = "zh") -> list[dict[str, str]]:
        index = 1 if lang == "zh" else 2
        return [{"key": o[0], "label": o[index]} for o in self.options]

    def option_keys(self) -> tuple[str, ...]:
        return tuple(o[0] for o in self.options)

    def score_scale(self, lang: str = "zh") -> dict | None:
        if self.scale is None:
            return None
        low, high, labels = self.scale
        index = 0 if lang == "zh" else 1
        return {"min": low, "max": high, "labels": [pair[index] for pair in labels]}

    def spec(self, *, lang: str = "zh", options=None, prompt: str | None = None) -> dict:
        """产出 README 2.1 的 questions[] 形状：{key,kind,prompt,options?|scale?}。"""
        text = prompt if prompt is not None else self.prompt(lang)
        if self.kind == "noul":
            return {"key": self.key, "kind": "noul", "prompt": text,
                    "options": [{"key": k, "label": label} for k, label in NOUL_OPTIONS[lang]]}
        if self.kind == "choice":
            pairs = ([{"key": str(o["key"]), "label": str(o["label"])} for o in options]
                     if options is not None else self.option_pairs(lang))
            return {"key": self.key, "kind": "choice", "prompt": text, "options": pairs}
        return {"key": self.key, "kind": "score", "prompt": text,
                "scale": self.score_scale(lang)}


def _noul(key: str, domains, criterion: str, zh: str, en: str, notes: str = "") -> QuestionKey:
    return QuestionKey(key, "noul", tuple(domains), criterion, zh, en, notes=notes)


def _choice(key: str, domains, criterion: str, zh: str, en: str, options: str,
            options_from_state: bool = False, notes: str = "") -> QuestionKey:
    return QuestionKey(key, "choice", tuple(domains), criterion, zh, en,
                       options=() if options_from_state else _options(options),
                       options_from_state=options_from_state, notes=notes)


def _score(key: str, domains, criterion: str, zh: str, en: str, levels: str,
           notes: str = "") -> QuestionKey:
    return QuestionKey(key, "score", tuple(domains), criterion, zh, en,
                       scale=_levels(levels), notes=notes)


_KEYS: list[QuestionKey] = [
    # ---- decision_mechanics：工具选择、下一步动作、计划、资格/权限
    _choice("action_selection", ("decision_mechanics",),
            "给定状态下的下一步动作类型：直接作答、调用工具、先澄清、拒绝或延后。",
            "在这个情境下，下一步最合适的动作是什么？",
            "What is the most appropriate next action in this situation?",
            "direct_answer=直接作答=direct answer|use_tool=调用工具=use a tool|"
            "ask_clarification=先澄清=ask for clarification|refuse=拒绝=refuse|"
            "defer=延后或转交=defer or hand off"),
    _choice("next_step_candidate", ("decision_mechanics",),
            "Open-Jev 型候选步骤：条目自带 2-16 个候选，答案只在其间选择。",
            "以下候选中，哪一个是正确的下一步？",
            "Which of the listed candidates is the correct next step?",
            "", options_from_state=True,
            notes="候选来自 state 本身；转换器必须用 build_question(key, options=...) 传入。"),
    _noul("tool_use_appropriate", ("decision_mechanics",),
          "是否需要外部工具（检索、计算、执行）而不是凭记忆作答。",
          "这一步是否需要调用外部工具？", "Does this step require an external tool?"),
    _noul("plan_feasible", ("decision_mechanics",),
          "给出的计划在当前约束（权限、预算、环境）下可执行。",
          "该计划在当前约束下可执行吗？", "Is the plan executable under the stated constraints?"),
    _noul("eligibility_granted", ("decision_mechanics",),
          "主体是否具备执行该动作的资格或权限（不等同于动作是否明智）。",
          "该主体有资格执行这个动作吗？", "Is the actor eligible to perform this action?"),
    _noul("information_sufficient", ("decision_mechanics", "knowledge_reasoning"),
          "现有信息是否足以做出决定，而不必先澄清。",
          "现有信息足以做出决定吗？", "Is the available information sufficient to decide?"),
    _score("risk_of_action", ("decision_mechanics",),
           "该动作产生未同意副作用的风险等级。",
           "这个动作的副作用风险有多高？", "How risky is the side effect of this action?",
           "无风险=none|轻微=minor|中等=moderate|高=high|极高=critical"),
    _noul("action_reversible", ("decision_mechanics",),
          "该动作是否可撤回或可无损撤销。",
          "这个动作可以撤回吗？", "Is this action reversible?"),

    # ---- human_judgment：真人判断与校准
    _choice("sentiment_polarity", ("human_judgment",),
            "文本整体情感倾向（不构成行为性质判断）。",
            "这段文本的整体情感倾向是什么？",
            "What is the overall sentiment polarity of the text?",
            "positive=正面=positive|negative=负面=negative|mixed=褒贬混合=mixed|neutral=中性=neutral"),
    _choice("emotion_primary", ("human_judgment",),
            "标注者感知到的主要情绪类别；情绪本身不是违规。",
            "这段文本传达的主要情绪是什么？",
            "Which primary emotion does the text convey?",
            "joy=喜悦=joy|sadness=悲伤=sadness|anger=愤怒=anger|fear=恐惧=fear|"
            "surprise=惊讶=surprise|disgust=厌恶=disgust|neutral=无明显情绪=neutral|other=其他=other"),
    _noul("toxicity_present", ("human_judgment", "risk_harm"),
          "文本是否含针对人或群体的敌意、侮辱或威胁（按行为判据，不按措辞激烈程度）。",
          "这段文本包含敌意、侮辱或威胁吗？",
          "Does the text contain hostility, insult, or threat?"),
    _score("toxicity_severity", ("human_judgment", "risk_harm"),
           "敌意/侮辱/威胁的严重程度分级。",
           "敌意或威胁的严重程度如何？", "How severe is the hostility or threat?",
           "无=none|轻微=minor|中等=moderate|严重=severe|极端=extreme"),
    _choice("toxicity_target", ("human_judgment", "risk_harm"),
            "敌意指向的对象；无对象时选 none。",
            "敌意指向谁？", "At whom is the hostility directed?",
            "none=无对象=none|self=自己=self|specific_person=具体个人=specific person|"
            "group=群体=group|institution=机构或制度=institution|other=其他=other"),
    _choice("entailment_relation", ("human_judgment", "knowledge_reasoning"),
            "前提与假设之间的蕴含关系（NLI 三值）。",
            "前提与假设之间是什么关系？", "What is the relation between premise and hypothesis?",
            "entailment=蕴含=entailment|neutral=中立=neutral|contradiction=矛盾=contradiction"),
    _choice("judgment_basis", ("human_judgment",),
            "判断主要依据行为事实、措辞语气、上下文还是身份标签（硬规则：不得用情绪或措辞当行为性质）。",
            "这个判断主要依据什么？", "What is this judgment mainly based on?",
            "behavior=行为事实=behavior|wording=措辞语气=wording|context=上下文=context|"
            "identity=身份标签=identity|unclear=无法确定=unclear"),

    # ---- social_moral：亲社会回应、道德规范、动机→行为→后果
    _noul("prosocial_response_warranted", ("social_moral",),
          "是否应当给出亲社会回应（支持、安抚、建设性行动），而不是直接阻断。",
          "这里是否需要亲社会回应？", "Is a prosocial response warranted here?"),
    _choice("moral_judgment", ("social_moral",),
            "对该行为的道德判断；只评行为，不给行为人贴等级。",
            "这个行为在道德上如何评价？", "How is the behavior morally judged?",
            "acceptable=可接受=acceptable|ambiguous=有争议=ambiguous|wrong=不当=wrong"),
    _choice("intent_motive", ("social_moral",),
            "行为者动机：帮助、伤害、中性、混合或不明。",
            "行为者的动机是什么？", "What is the actor's motive?",
            "helpful=帮助=helpful|harmful=伤害=harmful|neutral=中性=neutral|"
            "mixed=混合=mixed|unclear=不明=unclear"),
    _choice("expected_consequence", ("social_moral",),
            "该行为预期造成的主要后果类型。",
            "这个行为会造成什么后果？", "What consequence does the behavior lead to?",
            "benefit=受益=benefit|harm=受损=harm|mixed=有好有坏=mixed|none=无后果=none|"
            "unclear=不明=unclear"),
    _noul("norm_violation", ("social_moral",),
          "是否违反所处语境中被明确承认的社会规范或规则。",
          "这违反了明确的社会规范或规则吗？",
          "Does this violate an explicit social norm or rule?"),
    _choice("moral_foundation", ("social_moral",),
            "该判断可归属的道德基础（Social Chemistry 维度）；无归属选 none。",
            "这涉及哪一类道德基础？", "Which moral foundation is involved?",
            "care=关怀与伤害=care/harm|fairness=公平与欺骗=fairness/cheating|"
            "loyalty=忠诚与背叛=loyalty/betrayal|authority=权威与颠覆=authority/subversion|"
            "sanctity=圣洁与堕落=sanctity/degradation|liberty=自由与压迫=liberty/oppression|"
            "none=无=none"),
    _noul("power_asymmetry", ("social_moral",),
          "互动双方是否存在权力、资源或信息的不对等（不对等本身不等于违规）。",
          "双方存在权力或资源不对等吗？", "Is there a power or resource asymmetry?"),

    # ---- risk_harm：伤害类别、越狱与对抗、升级
    _noul("contains_harm", ("risk_harm", "pol2_axis"),
          "情境中是否包含对任何主体的伤害，无论是否直接蓄意。",
          "这个情境包含对他人的伤害吗？",
          "Does the situation involve harm to anyone?"),
    _noul("violent_intent", ("risk_harm", "pol2_axis"),
          "是否表达或邀约对他人施加暴力的意图（区别于陈述受害经历或求助）。",
          "这里有施加暴力的意图吗？", "Is there intent to do violence?"),
    _choice("harm_category", ("risk_harm",),
            "伤害的主要类别；多项时取最严重的一项。",
            "这属于哪一类伤害？", "Which category of harm is this?",
            "physical=身体伤害=physical|psychological=心理伤害=psychological|"
            "sexual=性相关伤害=sexual|financial=财产与经济损失=financial|"
            "privacy=隐私侵害=privacy|illegal=违法协助=illegal|self_harm=自我伤害=self-harm|"
            "cyber=网络与系统攻击=cyber|ecological=生态伤害=ecological|none=无伤害=none|"
            "other=其他=other"),
    _score("harm_severity", ("risk_harm", "pol2_axis"),
           "伤害严重程度 0-4，0 表示无伤害；分级依据后果而非措辞强度。",
           "伤害的严重程度如何？", "How severe is the harm?",
           "无伤害=none|轻微=minor|中等=moderate|严重=severe|灾难性=catastrophic"),
    _choice("harm_target", ("risk_harm",),
            "伤害指向的对象。",
            "伤害指向谁？", "Who is the target of the harm?",
            "none=无对象=none|self=自己=self|specific_person=具体个人=specific person|"
            "group=群体=group|vulnerable_group=脆弱群体=vulnerable group|"
            "public=公众=the public|other=其他=other"),
    _choice("harm_timing", ("risk_harm",),
            "伤害的时间位置：已发生、正在发生、即将发生或不明。",
            "伤害发生在什么时候？", "When does the harm occur?",
            "none=无伤害=none|past=已发生=past|ongoing=正在发生=ongoing|"
            "imminent=即将发生=imminent|unclear=不明=unclear"),
    _noul("jailbreak_attempt", ("risk_harm",),
          "是否试图绕过安全约束或诱导越权输出（对抗性框架）。",
          "这包含越狱或对抗性诱导吗？", "Is this a jailbreak or adversarial attempt?"),
    _noul("injection_present", ("risk_harm", "pol2_axis"),
          "是否存在来自不可信文档/网页的伪装指令（对应本体 untrusted_instruction_injection）。",
          "这里存在不可信来源的注入指令吗？",
          "Is there an injected instruction from an untrusted source?"),
    _noul("escalation_needed", ("risk_harm", "pol2_axis"),
          "是否需要升级到人工复核或更高处置层级。",
          "这件事需要升级处理吗？", "Does this need escalation?"),
    _noul("refusal_appropriate", ("risk_harm",),
          "拒绝该请求是否恰当（不因措辞或情绪而误拒）。",
          "拒绝这个请求是否恰当？", "Is refusing this request appropriate?"),

    # ---- knowledge_reasoning：常识与知识型判断
    _noul("claim_supported", ("knowledge_reasoning",),
          "陈述是否被给定上下文或既有事实支持。",
          "这个陈述有依据支持吗？", "Is the claim supported by evidence?"),
    _noul("commonsense_plausible", ("knowledge_reasoning",),
          "是否符合常识与物理/社会世界的基本规律。",
          "这符合常识吗？", "Is this consistent with common sense?"),
    _noul("reasoning_valid", ("knowledge_reasoning",),
          "推理步骤是否有效（前提为真时结论是否成立）。",
          "这个推理有效吗？", "Is the reasoning valid?"),
    _choice("evidence_sufficiency", ("knowledge_reasoning", "pol2_axis"),
            "证据三值（本体 evidence 枚举）：充分 / 不足 / 冲突。",
            "现有证据属于哪一种？", "How sufficient is the evidence?",
            "sufficient=证据充分=sufficient|insufficient=证据不足=insufficient|"
            "contradictory=证据冲突=contradictory"),
    _score("answer_uncertainty", ("knowledge_reasoning",),
           "答案的不确定程度 0-4（0 为确定）；不是模型置信度的替代品。",
           "这个答案有多不确定？", "How uncertain is the answer?",
           "确定=certain|较确定=mostly certain|中等=moderate|较不确定=uncertain|"
           "完全不确定=unknown"),
    _choice("knowledge_source", ("knowledge_reasoning",),
            "判断所依赖的知识来源；不明时选 unknown。",
            "这个判断依赖哪类知识？", "Which knowledge source supports the judgment?",
            "world_knowledge=世界知识=world knowledge|provided_context=给定上下文=provided context|"
            "common_sense=常识=common sense|expert_consensus=专家共识=expert consensus|"
            "unknown=不明=unknown"),
    _noul("question_well_formed", ("knowledge_reasoning",),
          "问题本身是否清晰、可判定（不是信息不足，而是问题不含混）。",
          "这个问题本身清晰可判定吗？", "Is the question itself well formed?"),

    # ---- pol2_axis：PoL2 判定轴
    _choice("interaction_polarity", ("pol2_axis",),
            "本体 polarity 四值：爱 / 恨 / 非爱非恨（不在场）/ 无法定性；恨不直接等于坏。",
            "这段互动的极性是什么？", "What is the polarity of this interaction?",
            "love=爱=love|hate=恨=hate|neither=非爱非恨（不在场）=neither|"
            "unclear=无法定性=unclear"),
    _choice("policy_status", ("pol2_axis",),
            "本体 status 三值：符合 / 违背 / 信息不足；信息不足不得当作恨。",
            "按 PoL2 政策，这个行为的状态是什么？",
            "What is the PoL2 policy status of this behavior?",
            "conforming=符合=conforming|violating=违背=violating|insufficient=信息不足=insufficient"),
    _choice("pol2_issue", ("pol2_axis",),
            "本条情境最主要的 PoL2 issue（15 条判定轴之一）；多 issue 叠加时用各 issue_* 键分别判断。",
            "这段情境最主要命中的 PoL2 问题是什么？",
            "Which PoL2 issue does this situation primarily match?",
            "|".join(f"{i}={zh}={en}" for i, zh, en, _ in POL2_ISSUES)),
    _noul("mitigation_applies", ("pol2_axis",),
          "是否命中本体 mitigations 的例外（值守安全的恨、正当批评、拒绝与异议、求救、修复、游戏边界、同意仍有效）。",
          "这里有需要防止误拦的例外情形吗？",
          "Does a false-positive mitigation apply here?"),
    _choice("mitigation", ("pol2_axis",),
            "命中的例外类别（本体 mitigations 枚举）；未命中选 none。",
            "命中的是哪一类例外？", "Which mitigation applies?",
            "none=未命中=none|" + "|".join(f"{i}={zh}={en}" for i, zh, en in POL2_MITIGATIONS)),
    _noul("love_language_present", ("pol2_axis",),
          "是否体现出某一种爱语（PoL.2.1-2.16）。",
          "这里体现出某种爱语吗？", "Does this express a love language?"),
    _choice("love_language", ("pol2_axis",),
            "体现的爱语类别（本体 love_languages 16 条）；爱语有边界，误用不算。",
            "体现的是哪一种爱语？", "Which love language is expressed?",
            "|".join(f"{i}={zh}={en}" for i, zh, en in POL2_LOVE_LANGUAGES),
            notes="love_language_present=noul 为 no 时不要给出本键答案。"),
    _choice("recommended_action", ("risk_harm", "pol2_axis"),
            "本体 actions 五动作：放行 / 修正后复查 / 阻止 / 澄清 / 复核；block 须是最后手段。",
            "建议采取哪个治理动作？", "Which governance action is recommended?",
            "|".join(f"{i}={zh}={en}" for i, zh, en in POL2_ACTIONS)),
    _choice("response_style", ("social_moral", "risk_harm"),
            "人际回应风格的升级梯度（任务描述里的 allow→escalate 阶梯）；治理动作仍用 recommended_action。",
            "建议采取哪种回应风格？", "Which response style is recommended?",
            "allow=放行=allow|respond_prosocially=亲社会回应=respond prosocially|"
            "deescalate=降温=de-escalate|warn=警示=warn|escalate=升级=escalate"),
    _choice("surface", ("pol2_axis",),
            "本体 surfaces 三值：用户输入 / 助手输出 / 工具行动。",
            "要判定的是哪一个面？", "Which surface is being judged?",
            "user_input=用户输入=user input|assistant_output=助手输出=assistant output|"
            "tool_action=工具行动=tool action"),
    _noul("boundary_assertion", ("pol2_axis",),
          "是否清晰表达自己的边界、接受范围或底线（PoL.2.1 诚实的一部分，不是违规）。",
          "这是在表达边界吗？", "Is this an assertion of boundaries?"),
    _noul("consent_withdrawn", ("pol2_axis",),
          "同意是否已被明确撤回（未撤回不等于撤回）。",
          "同意被明确撤回了么？", "Has consent been explicitly withdrawn?"),
    _choice("consent_status", ("pol2_axis",),
            "持续同意状态：不适用 / 已给出且有效 / 已撤回 / 不明。",
            "同意处于什么状态？", "What is the consent status?",
            "not_applicable=不适用=not applicable|granted=已给出且有效=granted|"
            "withdrawn=已撤回=withdrawn|unclear=不明=unclear"),
    _noul("fabricated_intimacy", ("pol2_axis",),
          "PAI 是否虚构人类的身体接触、血缘或浪漫亲密（本体 fabricated_intimacy）。",
          "这里存在虚构亲密吗？", "Is there fabricated intimacy?"),
    _noul("emotion_state_claim", ("pol2_axis",),
          "PAI 是否断言用户未表达的情感状态（本体 emotion_state_detection）。",
          "这里在断言用户未表达的情绪吗？",
          "Does this assert an unexpressed emotional state?"),
    _choice("person_vs_behavior", ("pol2_axis",),
            "评价对象是人还是行为（平等对待人 ≠ 平等对待行为）。",
            "这里评价的是人还是行为？", "Does this judge the person or the behavior?",
            "about_behavior=针对行为=about behavior|about_person=针对人=about the person|"
            "both=两者都有=both|unclear=不明=unclear"),
    _choice("criticism_vs_attack", ("pol2_axis",),
            "是正当批评还是人身攻击；认定攻击须有行为判据，措辞激烈不算。",
            "这是批评还是攻击？", "Is this criticism or a personal attack?",
            "behavior_criticism=正当批评=legitimate criticism|person_attack=人身攻击=personal attack|"
            "both=两者都有=both|unclear=不明=unclear"),
    _noul("public_interest", ("pol2_axis",),
          "行为是否以公共性为取向（知识、资源、决策的开放与共享）。",
          "这以公共利益为取向吗？", "Is this oriented to the public interest?"),
    _noul("care_intent", ("pol2_axis",),
          "是否出于关怀意图；关怀与控制可以同时成立，须分别判断。",
          "这里有关怀意图吗？", "Is there caring intent?"),
    _noul("control_intent", ("pol2_axis",),
          "是否试图通过恐惧、内疚、依赖或信息封锁取得控制地位。",
          "这里存在控制意图吗？", "Is there controlling intent?"),
    _noul("nonpolar_absence", ("pol2_axis",),
          "是否属于「不在场」（干扰、疾病、理解偏差造成的误会）：不是违规，不得道德化。",
          "这属于非爱非恨的不在场情形吗？",
          "Is this a non-polar absence rather than love or hate?"),
]

#: 15 条判定轴的二元键（id 与本体一致，供逐轴覆盖统计）
for _issue_id, _issue_zh, _issue_en, _issue_criterion in POL2_ISSUES:
    _KEYS.append(_noul(
        f"issue_{_issue_id}", ("pol2_axis",), _issue_criterion,
        f"该情境是否构成「{_issue_zh}」？",
        f"Does the situation constitute \"{_issue_en}\"?",
        notes="与本体 issues[].id 一一对应；多 issue 可同时为 yes。",
    ))
del _issue_id, _issue_zh, _issue_en, _issue_criterion

QUESTION_KEYS: dict[str, QuestionKey] = {q.key: q for q in _KEYS}

#: 每个覆盖域可用的全部问题键（定义顺序）
DOMAIN_KEYS: dict[str, tuple[str, ...]] = {
    domain: tuple(q.key for q in _KEYS if domain in q.domains) for domain in DOMAINS
}

#: 每个域的最小问题集：转换器默认至少带上这些键
CORE_KEYS: dict[str, tuple[str, ...]] = {
    "decision_mechanics": ("action_selection", "information_sufficient", "risk_of_action"),
    "human_judgment": ("sentiment_polarity", "toxicity_present", "judgment_basis"),
    "social_moral": ("prosocial_response_warranted", "moral_judgment", "intent_motive"),
    "risk_harm": ("contains_harm", "harm_severity", "recommended_action"),
    "knowledge_reasoning": ("claim_supported", "evidence_sufficiency", "answer_uncertainty"),
    "pol2_axis": ("interaction_polarity", "policy_status", "recommended_action", "evidence_sufficiency"),
}

POL2_AXIS_KEYS: tuple[str, ...] = tuple(f"issue_{i}" for i, _, _, _ in POL2_ISSUES)

ID_PATTERN = r"^db-[A-Za-z0-9._-]+-[0-9a-f]{8}$"


def resolve_key(key: str) -> str:
    """把别名或规范键名解析成规范键名；未知键抛 KeyError。"""
    if key in QUESTION_KEYS:
        return key
    alias = QUESTION_KEY_ALIASES.get(key)
    if alias is not None:
        return alias
    raise KeyError(f"未知问题键 {key!r}；taxonomy 只有 {len(QUESTION_KEYS)} 个键，"
                   f"可用 DOMAIN_KEYS[domain] 查看某域的全部键")


def key_spec(key: str) -> QuestionKey:
    """取问题键定义（接受别名）。"""
    return QUESTION_KEYS[resolve_key(key)]


def keys_for_domain(domain: str) -> tuple[str, ...]:
    if domain not in DOMAIN_KEYS:
        raise KeyError(f"未知覆盖域 {domain!r}；合法值：{', '.join(DOMAINS)}")
    return DOMAIN_KEYS[domain]


def core_keys(domain: str) -> tuple[str, ...]:
    if domain not in CORE_KEYS:
        raise KeyError(f"未知覆盖域 {domain!r}；合法值：{', '.join(DOMAINS)}")
    return CORE_KEYS[domain]


def build_question(key: str, *, lang: str = "zh", options=None, prompt: str | None = None) -> dict:
    """构造一个符合 README 2.1 的 questions[] 条目。

    options 只允许用于 options_from_state=True 的键（如 next_step_candidate）。
    """
    if lang not in NOUL_OPTIONS:
        raise ValueError(f"lang 只支持 {sorted(NOUL_OPTIONS)}，收到 {lang!r}")
    spec = key_spec(key)
    if spec.kind == "noul":
        if options is not None:
            raise ValueError(f"{spec.key}: noul 的选项固定为 yes/no，不接受 options 覆盖")
        question = spec.spec(lang=lang, prompt=prompt)
    elif spec.kind == "choice":
        if options is None:
            if spec.options_from_state:
                raise ValueError(
                    f"{spec.key}: 选项来自条目本身，必须传 options=[{{'key':...,'label':...}}, ...]")
            question = spec.spec(lang=lang, prompt=prompt)
        else:
            if not spec.options_from_state:
                raise ValueError(f"{spec.key}: 选项由 taxonomy 固定，不接受覆盖（避免同义标签）")
            question = spec.spec(lang=lang, options=options, prompt=prompt)
    else:
        question = spec.spec(lang=lang, prompt=prompt)
    errors = validate_question(question)
    if errors:
        raise ValueError("；".join(errors))
    return question


def build_questions(domain: str, keys=None, *, lang: str = "zh") -> list[dict]:
    """按覆盖域构造问题列表；keys 省略时用 CORE_KEYS[domain]。"""
    keys_for_domain(domain)
    selected = core_keys(domain) if keys is None else tuple(keys)
    if not selected:
        raise ValueError(f"{domain}: 问题键不能为空")
    return [build_question(key, lang=lang) for key in selected]


def validate_question(question) -> list[str]:
    """校验一个 questions[] 条目是否与 taxonomy 一致；返回错误串列表（空为通过）。"""
    if not isinstance(question, dict):
        return ["问题不是 JSON 对象"]
    raw_key = question.get("key")
    if not isinstance(raw_key, str) or not raw_key:
        return ["问题缺 key"]
    try:
        spec = key_spec(raw_key)
    except KeyError as exc:
        return [str(exc)]
    errors: list[str] = []
    if raw_key != spec.key:
        errors.append(f"{spec.key}: 使用了别名 {raw_key!r}，入库必须用规范键名")
    kind = question.get("kind")
    if kind != spec.kind:
        errors.append(f"{spec.key}: kind={kind!r} 与 taxonomy 的 {spec.kind!r} 不一致")
    prompt = question.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append(f"{spec.key}: prompt 必须是非空字符串")
    if spec.kind == "noul":
        options = question.get("options")
        expected = [k for k, _ in NOUL_OPTIONS["zh"]]
        if not isinstance(options, list) or \
                [o.get("key") for o in options if isinstance(o, dict)] != expected:
            errors.append(f"{spec.key}: noul 的 options 必须是 {expected}")
    elif spec.kind == "choice":
        errors += _choice_option_errors(spec, question.get("options"))
    else:
        errors += _scale_errors(spec, question.get("scale"))
    return errors


def _choice_option_errors(spec: QuestionKey, options) -> list[str]:
    errors: list[str] = []
    if not isinstance(options, list):
        return [f"{spec.key}: choice 必须有 options 数组"]
    if not (MIN_CHOICE_OPTIONS <= len(options) <= MAX_CHOICE_OPTIONS):
        errors.append(f"{spec.key}: 选项数 {len(options)} 越界 "
                      f"[{MIN_CHOICE_OPTIONS},{MAX_CHOICE_OPTIONS}]")
    keys: list[str] = []
    for option in options:
        if not isinstance(option, dict):
            errors.append(f"{spec.key}: 选项必须是对象")
            continue
        okey, label = option.get("key"), option.get("label")
        if not isinstance(okey, str) or not okey:
            errors.append(f"{spec.key}: 选项缺非空 key")
            continue
        if not isinstance(label, str) or not label.strip():
            errors.append(f"{spec.key}: 选项 {okey} 缺非空 label")
        if okey in keys:
            errors.append(f"{spec.key}: 选项 key 重复 {okey}")
        keys.append(okey)
    if not spec.options_from_state:
        expected = set(spec.option_keys())
        if set(keys) != expected:
            missing = sorted(expected - set(keys))
            extra = sorted(set(keys) - expected)
            errors.append(f"{spec.key}: 选项与 taxonomy 不一致（缺 {missing}，多 {extra}）")
    return errors


def _scale_errors(spec: QuestionKey, scale) -> list[str]:
    if not isinstance(scale, dict):
        return [f"{spec.key}: score 必须有 scale 对象"]
    errors: list[str] = []
    low, high = scale.get("min"), scale.get("max")
    if isinstance(low, bool) or isinstance(high, bool) or \
            not isinstance(low, int) or not isinstance(high, int):
        return [f"{spec.key}: scale.min/max 必须是整数"]
    if high < low:
        errors.append(f"{spec.key}: scale.max {high} < min {low}")
    labels = scale.get("labels")
    if not isinstance(labels, list) or len(labels) != high - low + 1:
        errors.append(f"{spec.key}: scale.labels 必须覆盖 {low}..{high} 共 {high - low + 1} 档")
    elif any(not isinstance(x, str) or not x.strip() for x in labels):
        errors.append(f"{spec.key}: scale.labels 必须都是非空字符串")
    if spec.scale is not None and (low, high) != spec.scale[:2]:
        errors.append(f"{spec.key}: scale 量程应为 {spec.scale[0]}..{spec.scale[1]}，收到 {low}..{high}")
    return errors


def normalize_option(key: str, value: str) -> str:
    """把旧选项值映射成规范选项 key；未知值抛 KeyError。"""
    spec = key_spec(key)
    aliases = LEGACY_VALUE_ALIASES.get(spec.key, {})
    if value in aliases:
        return aliases[value]
    allowed = set(spec.option_keys()) | {"yes", "no"}
    if value not in allowed:
        raise KeyError(f"{spec.key}: 取值 {value!r} 不在 {sorted(allowed)}")
    return value


def normalize_answer(key: str, answer):
    """把布尔等旧写法归一到规范答案：True→"yes"、False→"no"；选项值走 normalize_option。"""
    spec = key_spec(key)
    if isinstance(answer, bool):
        if spec.kind != "noul":
            raise KeyError(f"{spec.key}: 只有 noul 接受布尔答案")
        return "yes" if answer else "no"
    if spec.kind in ("noul", "choice") and isinstance(answer, str):
        return normalize_option(spec.key, answer)
    return answer


def validate_target(key: str, value) -> list[str]:
    """校验 targets[key] = {answer?, probs?}；返回错误串列表（空为通过）。"""
    try:
        spec = key_spec(key)
    except KeyError as exc:
        return [str(exc)]
    if value is None:
        return []
    if not isinstance(value, dict):
        return [f"{spec.key}: target 必须是对象 {{answer?, probs?}}"]
    errors: list[str] = []
    answer = value.get("answer")
    if answer is not None:
        if spec.kind == "noul":
            if not (isinstance(answer, bool) or answer in ("yes", "no")):
                errors.append(f"{spec.key}: noul 答案必须是 'yes'/'no'（或布尔），收到 {answer!r}")
        elif spec.kind == "choice":
            if not isinstance(answer, str) or not answer:
                errors.append(f"{spec.key}: choice 答案必须是非空字符串，收到 {answer!r}")
            elif not spec.options_from_state and answer not in set(spec.option_keys()):
                errors.append(f"{spec.key}: 答案 {answer!r} 不在选项 {list(spec.option_keys())}")
        else:
            low, high = (spec.scale[0], spec.scale[1]) if spec.scale else (0, 0)
            if isinstance(answer, bool) or not isinstance(answer, int):
                errors.append(f"{spec.key}: score 答案必须是 {low}..{high} 的整数，收到 {answer!r}")
            elif not low <= answer <= high:
                errors.append(f"{spec.key}: score 答案 {answer} 越界 {low}..{high}")
    errors += _prob_errors(spec, value.get("probs"))
    return errors


def _prob_errors(spec: QuestionKey, probs) -> list[str]:
    if probs is None:
        return []
    if not isinstance(probs, dict) or not probs:
        return [f"{spec.key}: probs 必须是非空对象"]
    errors: list[str] = []
    total = 0.0
    for raw, prob in probs.items():
        if isinstance(prob, bool) or not isinstance(prob, (int, float)):
            errors.append(f"{spec.key}: probs[{raw!r}] 必须是数字")
            continue
        if not 0.0 <= float(prob) <= 1.0:
            errors.append(f"{spec.key}: probs[{raw!r}]={prob} 越界 [0,1]")
            continue
        total += float(prob)
        text = str(raw)
        if spec.kind == "noul" and text not in ("yes", "no"):
            errors.append(f"{spec.key}: probs 键 {raw!r} 不是 yes/no")
        elif spec.kind == "choice" and not spec.options_from_state and text not in set(spec.option_keys()):
            errors.append(f"{spec.key}: probs 键 {raw!r} 不在选项内")
        elif spec.kind == "score" and spec.scale is not None:
            low, high = spec.scale[0], spec.scale[1]
            try:
                level = int(text)
            except ValueError:
                errors.append(f"{spec.key}: probs 键 {raw!r} 不是整数分级")
                continue
            if not low <= level <= high:
                errors.append(f"{spec.key}: probs 键 {level} 越界 {low}..{high}")
    if not errors and abs(total - 1.0) > 1e-3:
        errors.append(f"{spec.key}: probs 之和 {total:.6f} 未归一到 1")
    return errors


def id_is_canonical(item_id: str) -> bool:
    """README 2.1 的 id 形状 db-<source-slug>-<8hex>。"""
    return bool(re.fullmatch(ID_PATTERN, item_id or ""))


def item_errors(item) -> list[str]:
    """按 README 2.1 校验一个条目；返回错误串列表（空为通过）。"""
    if not isinstance(item, dict):
        return ["条目不是 JSON 对象"]
    errors: list[str] = []
    for field_name in ("id", "domain", "lang", "state", "questions", "source", "meta"):
        if field_name not in item:
            errors.append(f"缺字段 {field_name}")
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        errors.append("id 必须是非空字符串")
    domain = item.get("domain")
    if domain not in DOMAINS:
        errors.append(f"domain={domain!r} 不在 taxonomy 的 6 个覆盖域内")
    lang = item.get("lang")
    if not isinstance(lang, str) or not lang.strip():
        errors.append("lang 必须是非空字符串")
    state = item.get("state")
    if not isinstance(state, str) or not state.strip():
        errors.append("state 必须是非空字符串")
    keys: list[str] = []
    questions = item.get("questions")
    if not isinstance(questions, list) or not questions:
        errors.append("questions 必须是非空数组")
    else:
        for index, question in enumerate(questions):
            errors += [f"questions[{index}]: {e}" for e in validate_question(question)]
            raw = question.get("key") if isinstance(question, dict) else None
            if isinstance(raw, str):
                canonical = QUESTION_KEY_ALIASES.get(raw, raw)
                if canonical in keys:
                    errors.append(f"questions[{index}]: 问题键重复 {canonical}")
                keys.append(canonical)
    targets = item.get("targets")
    if targets is None:
        targets = {}
    if not isinstance(targets, dict):
        errors.append("targets 必须是对象")
    else:
        for raw_key, value in targets.items():
            try:
                spec = key_spec(raw_key)
            except KeyError as exc:
                errors.append(f"targets: {exc}")
                continue
            if spec.key not in keys:
                errors.append(f"targets[{raw_key}]: 没有对应的 questions 条目")
            errors += [f"targets[{raw_key}]: {e}" for e in validate_target(spec.key, value)]
    source = item.get("source")
    if not isinstance(source, dict):
        errors.append("source 必须是对象")
    else:
        for field_name in ("dataset", "revision", "config", "split", "row", "license", "url"):
            if field_name not in source:
                errors.append(f"source 缺字段 {field_name}")
    meta = item.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta 必须是对象")
    else:
        for field_name in ("converter", "converter_version", "created_at"):
            if field_name not in meta:
                errors.append(f"meta 缺字段 {field_name}")
    return errors


# ---------------------------------------------------------------- 本体漂移检查

def load_ontology(path: Path | str | None = None) -> dict:
    return json.loads(Path(path or ONTOLOGY_PATH).read_text(encoding="utf-8"))


def ontology_mismatches(path: Path | str | None = None) -> list[str]:
    """与 PoL2 本体逐项对比；返回不一致描述（空表示对齐，文件缺失也算不一致）。"""
    target = Path(path or ONTOLOGY_PATH)
    if not target.is_file():
        return [f"本体文件不存在: {target}"]
    try:
        data = load_ontology(target)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"本体无法解析: {exc}"]
    problems: list[str] = []
    # 本体只有 issues / love_languages 带 en 字段，其余节仅有 id/key + zh；
    # 只比对本体真正声明的字段，英文名是本文件自带的展示用注释。
    checks = (
        ("issues", POL2_ISSUES, ("id", "zh", "en"), ("id", "zh", "en")),
        ("love_languages", POL2_LOVE_LANGUAGES, ("id", "zh", "en"), ("id", "zh", "en")),
        ("mitigations", POL2_MITIGATIONS, ("id", "zh"), ("id", "zh", "en")),
        ("actions", POL2_ACTIONS, ("key", "zh"), ("key", "zh", "en")),
        ("status", POL2_STATUS, ("key", "zh"), ("key", "zh", "en")),
        ("polarity", POL2_POLARITY, ("key", "zh"), ("key", "zh", "en")),
        ("evidence", POL2_EVIDENCE, ("key", "zh"), ("key", "zh", "en")),
        ("surfaces", POL2_SURFACES, ("key", "zh"), ("key", "zh", "en")),
    )
    for section, expected_rows, ontology_fields, row_fields in checks:
        rows = data.get(section)
        if not isinstance(rows, list):
            problems.append(f"{section}: 本体缺该节")
            continue
        index = {name: i for i, name in enumerate(row_fields)}
        expected = [tuple(row[index[f]] for f in ontology_fields) for row in expected_rows]
        actual = [tuple(str(row.get(f)) for f in ontology_fields) for row in rows]
        if expected != actual:
            problems.append(f"{section}: 与本体不一致（本体 {len(actual)} 条，taxonomy {len(expected)} 条）"
                            f" missing={[r for r in expected if r not in actual]}"
                            f" unexpected={[r for r in actual if r not in expected]}")
    return problems


def summary() -> dict:
    """供覆盖报告与人工核对用的自描述摘要。"""
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "domains": list(DOMAINS),
        "kinds": list(KINDS),
        "keys": len(QUESTION_KEYS),
        "key_kinds": {
            kind: sum(1 for spec in QUESTION_KEYS.values() if spec.kind == kind)
            for kind in KINDS
        },
        "per_domain": {
            domain: {"keys": len(DOMAIN_KEYS[domain]), "core": len(CORE_KEYS[domain])}
            for domain in DOMAINS
        },
        "per_domain_kinds": {
            domain: {
                kind: sum(1 for key in DOMAIN_KEYS[domain] if QUESTION_KEYS[key].kind == kind)
                for kind in KINDS
            }
            for domain in DOMAINS
        },
        "pol2_axes": list(POL2_AXIS_KEYS),
    }


if __name__ == "__main__":
    print(json.dumps(summary(), ensure_ascii=False, indent=2))
    problems = ontology_mismatches()
    if problems:
        raise SystemExit("本体漂移：\n- " + "\n- ".join(problems))
