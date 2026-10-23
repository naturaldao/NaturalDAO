# Causal evaluation of PoL2 task execution

## What contrast can identify a PoL2 contribution?

### Takeaway

Keep the typed decision model, simulator, action set, state input, and goal predicate fixed; vary the policy instruction and runtime gate as independent factors. The primary content contrast is PoL2 versus a structurally and token-matched neutral instruction with the gate disabled in a sandbox; a crossed gate factor then estimates what the deterministic monitor adds to safety and task utility.

### Cited Findings

- The current public Kev screen uses 16 researcher-authored synthetic cases. Generic, token-matched neutral, and PoL2 conditions each matched the prewritten action label on 13/16 cases and each selected one forbidden action; neutral and PoL2 selected different actions in four cases, with two correctness gains and two losses. These are action-choice outcomes, not simulator task executions. [Current PoL2 experiment record](https://github.com/naturaldao/NaturalDAO/blob/main/Research/PoL2%E5%85%B7%E8%BA%AB%E6%8E%A8%E7%90%86%E8%BF%87%E7%A8%8B%E5%88%9D%E6%AD%A5%E9%AA%8C%E8%AF%81.md)
- In the same report, the VirtualHome pilot covers one hand-built task family, two authorization states, and four unique model inputs. Its deterministic gate blocks an injected unauthorized action, while the PoL2 prompt also changes a permitted-state choice from delivery to waiting. This establishes a working symbol-level gate probe and a potential false-refusal mode, not a general effect estimate. [Current PoL2 experiment record](https://github.com/naturaldao/NaturalDAO/blob/main/Research/PoL2%E5%85%B7%E8%BA%AB%E6%8E%A8%E7%90%86%E8%BF%87%E7%A8%8B%E5%88%9D%E6%AD%A5%E9%AA%8C%E8%AF%81.md)
- The NeurIPS 2024 Embodied Agent Interface separates goal interpretation, subgoal decomposition, action sequencing, and transition modeling, and includes error-specific measures such as hallucination, affordance, and planning errors. This supports evaluating both final execution and the stage where a failure entered the action chain. [EAI, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/b631da756d1573c24c9ba9c702fde5a9-Abstract-Datasets_and_Benchmarks_Track.html)
- AgentDojo reports benign utility, utility under attack, and targeted attack success rate together; it defines the utility-under-attack case using both completion of the legitimate task and absence of adversarial side effects. This is a directly relevant benchmark precedent for reporting constraint compliance and legitimate-task retention jointly. [AgentDojo, NeurIPS 2024](https://papers.nips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf)

### Inferences

- Use a **3 × 2 factorial** on one pinned typed-choice model: prompt condition `{generic, token/structure-matched neutral, PoL2}` × deterministic PoL2 gate `{off, on}`. Run gate-off only in an isolated simulator. The gate must be crossed with all three prompts; otherwise “PoL2 prompt” and “PoL2 gate” remain confounded. The causal prompt contrast is PoL2 versus neutral within the same gate stratum; the gate contrast is on versus off within each prompt; the interaction indicates whether model prompting changes the value of enforcement.
- Treat `generic → matched neutral` as a prompt-expansion control, and `matched neutral → PoL2` as the primary content comparison. Match model-reported input tokens, response schema, candidate count, and request order protocol; record the actual serialized requests, checkpoint, sampler settings, and outputs. Token equality removes only a length difference, not wording or semantic specificity.
- Freeze the PoL2 clause-to-world-state mapping before evaluation. Encode each run as: `observation → typed state/uncertainty → typed action distribution → gate allow/deny → simulator action → new observation → goal/constraint predicates`. Measure executed transitions and final state, not explanations emitted by the model.
- The theory-to-contract mapping is itself a premise, not a discovered “ground truth.” Automated checks can prove conformance to a frozen executable contract; they cannot prove that this contract is the uniquely correct interpretation of PoL2. An all-AI runtime is compatible with a versioned, frozen contract and independent automated evaluation, but it does not remove this normative specification gap.

### Gaps

- The current 16 cases were used to develop and revise prompts, labels, and metrics. Treat them as development/public regression cases, not a confirmatory holdout; split future data by task family and preserve a new unseen set. [Repository evaluation/data rules](https://github.com/naturaldao/NaturalDAO/blob/main/PoL-Governance/AGENTS.md)
- The public pilot has no independent audit of its operational oracle, no multi-family simulator executions, and no sample-size calculation for a target effect. A token-matched screen alone cannot repair these limits. [Current PoL2 experiment record](https://github.com/naturaldao/NaturalDAO/blob/main/Research/PoL2%E5%85%B7%E8%BA%AB%E6%8E%A8%E7%90%86%E8%BF%87%E7%A8%8B%E5%88%9D%E6%AD%A5%E9%AA%8C%E8%AF%81.md)

## What is the right trial unit and comparison structure?

### Takeaway

The unit should be a complete closed-loop episode, paired across conditions by task-family instance and simulator seed. Each episode must start from an identical reset, expose only run-time observations to the model, execute the selected action through the gate and adapter, and continue until a state-based goal, violation, timeout, or recovery limit is reached.

### Cited Findings

- CALVIN’s official evaluation interface resets an agent at the beginning of an evaluation sequence and calls `step(obs, goal)` repeatedly, returning an action each step; the benchmark resets the robot to a neutral position before every multi-step sequence to avoid initial-position bias. This supplies a concrete precedent for a reusable reset/step episode contract rather than scoring isolated model calls. [CALVIN official repository and evaluation protocol](https://github.com/mees/calvin)
- CALVIN evaluates language-conditioned continuous-control tasks over multi-step sequences and exposes varying sensor suites and training-environment splits. The reportable object is therefore a rollout with an initial condition and a task sequence, not an independent count of every action token. [CALVIN official repository](https://github.com/mees/calvin)
- SIMPLER reports more than 1,500 paired simulation/real evaluations across two robot embodiments and eight task families, and explicitly studies control/visual differences between real and simulated conditions. This shows that simulator results can scale evaluation, but simulator fidelity and sim-to-real validation remain separate evidence questions. [Li et al., CoRL/PMLR 2025](https://proceedings.mlr.press/v270/li25c.html)
- The robot-evaluation best-practices paper identifies missing run counts, initial conditions, success criteria, statistical analysis, and failure descriptions as common reporting weaknesses; it recommends explicit experimental conditions, complementary metrics, statistical analysis, and failure-mode narratives. [Kress-Gazit et al., “Robot Learning as an Empirical Science”](https://arxiv.org/abs/2409.09491)

### Inferences

- Construct each task family as paired states that share the task, scene, candidate actions, and initial seed but differ in one decision-relevant fact: e.g., authorization valid/revoked/unknown; shared resource available/occupied; path clear/occupied; object identity visible/occluded; task still feasible/already complete. Include both compliant-and-completable states and true refusal states, so an always-deny policy cannot score well.
- Randomize prompt/gate arm execution order within each paired scene; reset the simulator and any model state between episodes. Keep the same `task_family_id`, `scene_seed`, `model_seed`, and perturbation manifest across paired arms, while using multiple seeds to estimate variability. Repeated calls on an identical deterministic request are not new independent task samples.
- The action candidate list should contain executable primitives with typed arguments and preconditions, not labels that imply capabilities the simulator lacks. The simulator must independently emit post-action state facts and evaluate terminal goal and violation predicates.
- Define episode stopping rules in advance: terminal success, policy violation, unrecoverable executor error, or fixed step/time limit. Log whether an action was proposed, rejected by the monitor, sent to the executor, completed, partially completed, or timed out; those are distinct failure points.

### Gaps

- Current VirtualHome Evolving Graph execution is symbolic rather than continuous physics. It cannot validate collision avoidance, actuator timing, perception noise, or control stability; those claims require a physics-based simulator and later separately justified real-world evaluation. [Current PoL2 experiment record](https://github.com/naturaldao/NaturalDAO/blob/main/Research/PoL2%E5%85%B7%E8%BA%AB%E6%8E%A8%E7%90%86%E8%BF%87%E7%A8%8B%E5%88%9D%E6%AD%A5%E9%AA%8C%E8%AF%81.md); [SIMPLER paper](https://proceedings.mlr.press/v270/li25c.html)
- No source establishes a defensible fixed number of episodes for this specific PoL2 effect. The required number depends on baseline rates, smallest effect of interest, scene-family variability, and target interval width; estimate it from a pilot and state those choices before running the confirmatory set. [Robot learning evaluation best practices](https://arxiv.org/abs/2409.09491)

## Which metrics and uncertainty support a defensible claim?

### Takeaway

Use balanced safety-and-utility outcomes at episode level, report paired differences with uncertainty, and break failures down by stage. Do not use raw action counts as independent trials or interpret structured traces as evidence of hidden reasoning.

### Cited Findings

- The robot-learning evaluation paper argues that success rate alone is insufficient and recommends reporting conditions, complementary metrics, statistical analysis, and qualitative failure modes. [Kress-Gazit et al.](https://arxiv.org/abs/2409.09491)
- AgentDojo’s three metrics separate benign task completion, legitimate-task completion without adversarial side effects, and attacker-goal execution. This prevents a defense from appearing effective solely because it blocks actions while also disabling ordinary tasks. [AgentDojo paper](https://papers.nips.cc/paper_files/paper/2024/file/97091a5177d8dc64b1da8bf3e1f6fb54-Paper-Datasets_and_Benchmarks_Track.pdf)
- NIST’s statistical testing report describes binomial confidence bounds for repeated independent pass/fail trials and notes exact Clopper–Pearson intervals when an approximation is unsuitable. Such bounds require a defined trial and assumptions; repeated steps within one episode do not automatically satisfy independence. [NIST IR 6129](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir6129.pdf)
- SureSim combines paired real/simulation evaluations with non-asymptotic confidence intervals to address simulator bias when inferring real-world performance. Its design is evidence that simulation-to-real claims require paired calibration data, not simply a successful simulation campaign. [Badithela et al., SureSim](https://arxiv.org/abs/2510.04354)

### Inferences

- Pre-register a compact primary outcome set: (1) unauthorized-execution rate = forbidden transitions actually executed / forbidden action opportunities; (2) valid-task completion rate = valid tasks reaching the goal / valid task episodes; (3) false-refusal rate = valid tasks denied or abandoned / valid task episodes; (4) end-to-end goal success without any violation. Also report monitor-block rate, action count, episode time, recovery success, invalid/unknown-state handling, and audit completeness.
- For each paired `(family, scene_seed)` calculate PoL2-minus-neutral differences in binary completion and violation outcomes. Show per-family counts, denominators, paired difference and interval; use family-clustered resampling or an appropriate paired binary procedure for aggregate inference. Report exact binomial intervals for within-arm event rates when independence assumptions apply. Select sample size for a predeclared smallest effect and precision target; do not infer a tiny violation probability from zero observed failures in a small suite.
- Include `always-deny` as a diagnostic lower bound on utility, `oracle contract executor` as an upper-bound diagnostic for the frozen contract, `gate-only` to isolate external enforcement, and `TDM-generic`/`TDM-neutral`/`TDM-PoL2` as policy-input arms. Keep the oracle and the evaluated model from sharing the answer label in the observation.
- Phrase conclusions in the evidence domain: e.g. “under the frozen contract, model revision, simulator version, scenario families and seeds tested, PoL2 reduced X and changed Y while retaining Z valid-task successes.” Avoid “PoL2 improved reasoning” unless a separate, validated mechanism study supports that interpretation.

### Gaps

- The current study cannot estimate how often PoL2 will affect a population of robot tasks: 16 cases with eight hand-authored families and one symbolic simulator scene family are too narrow, and the oracle has not been independently validated. [Current PoL2 experiment record](https://github.com/naturaldao/NaturalDAO/blob/main/Research/PoL2%E5%85%B7%E8%BA%AB%E6%8E%A8%E7%90%86%E8%BF%87%E7%A8%8B%E5%88%9D%E6%AD%A5%E9%AA%8C%E8%AF%81.md)
- Simulator fidelity cannot be inferred from benchmark task success. SIMPLER’s paired results are specific to its environments and tested policy families; this project would need its own later transfer design before making claims about a physical robot. [SIMPLER paper](https://proceedings.mlr.press/v270/li25c.html)
