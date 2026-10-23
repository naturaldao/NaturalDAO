# Physically grounded simulator choice

## Which simulator can run the first physical demo on the current Windows CPU setup?

### Takeaway

Use the native `mujoco` Python package as the first physics backend, with a fixed tabletop manipulation scene and a named, short-horizon action adapter. Do not make the first milestone depend on Gymnasium-Robotics, PyBullet, ManiSkill rendering, or Isaac Lab: their documented Windows support, package availability, or hardware needs are a poorer fit for the current Windows/Python 3.12–3.13, CPU-first workspace.

### Cited Findings

- MuJoCo’s current Python bindings are distributed on PyPI, install with `pip install mujoco`, bundle the native library, and document explicit `MjModel`/`MjData`, stepping, state access and reset APIs. The documentation describes its computation as deterministic for a specific input ([MuJoCo Python API](https://mujoco.readthedocs.io/en/stable/python.html)).
- Current MuJoCo PyPI release artifacts include Windows x86-64 wheels for CPython 3.12 and 3.13; the current release metadata says Python >=3.10. This makes the native binding compatible in principle with the Python generations already used locally, though it does not prove the full application install or viewer works on this machine ([MuJoCo on PyPI](https://pypi.org/project/mujoco/)).
- Google DeepMind’s MuJoCo Menagerie includes articulated arms such as Franka Panda and FR3 with per-model licensing; the project specifically warns that each model directory has its own license, so the selected asset’s license must be copied/recorded separately ([MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie)).
- Gymnasium-Robotics’ Fetch Pick-and-Place task is a useful design reference: it exposes a 4-D action containing Cartesian end-effector displacement and gripper opening/closing; the 7-DoF Fetch controller uses internal inverse kinematics, and the observation contains simulated gripper/object state and goal coordinates ([Fetch Pick-and-Place documentation](https://robotics.farama.org/envs/fetch/pick_and_place/)).
- Gymnasium-Robotics currently documents Linux/macOS testing and explicitly says Windows is not officially supported, even though the underlying MuJoCo Python package itself publishes Windows wheels ([Gymnasium-Robotics installation](https://robotics.farama.org/content/installation/); [MuJoCo Python API](https://mujoco.readthedocs.io/en/stable/python.html)).
- The official PyBullet PyPI project’s current release is 3.2.7 (uploaded 2025-01-30); the published CPython wheels shown there are Linux wheels, and the release file list contains no `win_amd64` wheel. Its own quickstart describes `DIRECT` mode, explicit `stepSimulation`, URDF loading, state queries, inverse kinematics, collision queries, and a CPU software renderer; however, packaging friction for the repository’s current Windows Python makes it a weaker first choice unless the team accepts a source build or a separate compatible environment ([PyBullet on PyPI](https://pypi.org/project/pybullet/); [PyBullet Quickstart Guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html)).
- ManiSkill says state-based simulation can run without extra dependencies and lists Windows CPU simulation as supported with limited overall Windows support; it also says rendering requires a GPU with Vulkan, while Windows GPU simulation is not supported. It is a plausible later option if the project adds a Linux/NVIDIA runner or needs richer task assets, but it is not the least-friction CPU-only visual demo path ([ManiSkill installation and system support](https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/installation.html)).
- Isaac Lab’s current install guidance targets Windows 11 or Ubuntu 22.04+, Python 3.12, at least 32 GB system RAM and 16 GB GPU VRAM for full Isaac Sim workflows. That is a later fidelity/scale tier, not a sensible first milestone for the current CPU-only prototype ([Isaac Lab installation](https://isaac-sim.github.io/IsaacLab/develop/source/setup/installation/index.html)).

### Inferences

- **Recommended first stack:** keep Kev’s inference service as-is; add a separate Python 3.13 MuJoCo execution process that uses a frozen MuJoCo release and a fixed Franka/Panda MJCF asset after recording that model directory’s license. Keep the interface between them JSON over local HTTP/stdin or a narrow in-process adapter. This avoids forcing the model server and physics environment to share import-heavy dependencies.
- Use the Gymnasium Fetch action semantics as a *contract reference*, not as an unverified Windows dependency: high-level actions map to bounded end-effector/cartesian primitives (approach, close, lift, move, lower, open), and the environment—not the model—owns the inverse-kinematics/controller loop. In phase one the model should choose among discrete typed options such as `inspect`, `transfer_authorized_object`, `wait`, and `abort`; it must never produce joint torques or arbitrary controller code.
- Use MuJoCo’s deterministic stepping for headless regression first. Treat visualization as optional and separate from simulation success: a no-renderer test can still verify rigid-body contacts and target-state predicates; whether the local graphics driver can open the viewer remains a separate smoke-test question.
- The permissions, task ownership, and policy version are not native MuJoCo physics variables. Represent them in the task contract/state adapter, and make the runtime gate check those fields before every irreversible primitive; retain simulator object pose/contact as physical truth. This is an engineering design inference, not a built-in feature of MuJoCo.

### Gaps

- No local smoke test has yet confirmed installing the current MuJoCo wheel beside the existing Kev environment, loading an official robot model, opening the viewer, or running an end-effector controller on this specific Windows machine.
- The official Gymnasium-Robotics package has a ready Fetch pick-and-place controller, but current docs disclaim Windows support. A Linux/WSL run could reduce controller implementation work, but WSL rendering, package compatibility and the current local model-serving setup have not been verified.
- MuJoCo physics does not supply the PoL2 task semantics, an authorization registry, image perception, ownership facts, or a tested high-level planner. A robot model alone is not an end-to-end governance demo.
- Exact model asset licensing is model-directory-specific in Menagerie; any adopted arm asset must be checked and its license notice retained before inclusion in the NaturalDAO repository.

## What physical action and observation boundary should bridge Kev to the simulator?

### Takeaway

Keep the typed model at the task-decision layer and let a deterministic adapter own continuous control. The minimum useful end-to-end test is not “model chose deliver”; it is “a typed option passed a current-state authorization check, executed a bounded controller primitive, changed physical object state, and caused a fresh observation and next decision.”

### Cited Findings

- Gymnasium-Robotics’ documented Fetch environment exposes the robot end-effector, object pose/velocity, gripper state, and desired/achieved goal separately; its task success can be defined against the object’s achieved goal, and its action is continuous Cartesian delta plus gripper control ([Fetch Pick-and-Place action, observation and success definitions](https://robotics.farama.org/envs/fetch/pick_and_place/)).
- MuJoCo exposes the native model/data state and explicit `mj_step`, `mj_forward` and `mj_resetData` calls; this lets an adapter own stepping and retrieve state after each bounded command ([MuJoCo Python API](https://mujoco.readthedocs.io/en/stable/python.html)).
- MuJoCo Menagerie provides robot MJCF assets but cautions that assets have individual license terms, which is important if the project copies a model into its own benchmark ([MuJoCo Menagerie license notice](https://github.com/google-deepmind/mujoco_menagerie)).
- PyBullet demonstrates an alternative simulation-control pattern: run `DIRECT`, issue one or more `stepSimulation` calls, then query object pose; direct mode avoids GUI/VR rendering, and its quickstart explicitly discusses headless software rendering ([PyBullet Quickstart Guide](https://github.com/bulletphysics/bullet3/blob/master/docs/pybullet_quickstart_guide/PyBulletQuickstartGuide.md.html)).

### Inferences

- The adapter should expose only named **macro-actions** with preconditions and postconditions, not raw low-level commands to Kev. Suggested schema fields: `episode_id`, `observation_revision`, `task_id`, `target_object_id`, `target_region_id`, `selected_action_id`, `permission_state` (`granted|denied|unknown`), `permission_scope`, `policy_version`, `deadline`, and `request_id`. The model selects from a fixed candidate list; the adapter rejects stale state revisions, unknown IDs, missing scope, out-of-bounds targets, and expired/unknown authorization.
- A guarded `transfer_authorized_object` macro-action should execute as short phases: approach → grasp → lift → transport → place → release. After each phase the adapter steps the simulator, checks contact/pose/limits, stores a new `observation_revision`, and either continues, asks Kev for a new typed decision, or enters a machine-controlled safe stop. The gate should re-check permission before grasp and before placement so a revocation/state change cannot be ignored by a long open-loop macro.
- Phase-one observations should deliberately be simulator-state-derived and labelled **privileged state** (object pose, grasp/contact flag, target relation, permission record). That isolates governance/action selection from vision errors. Phase two should add camera images, a perception component, and an explicit `unknown` state to evaluate whether visual uncertainty changes policy decisions; do not pass ground-truth object labels to the typed model while claiming perception evaluation.
- Use task-episode IDs and fixed initial states/seeds; record exact model/checkpoint/prompt/policy/simulator revisions, every typed request/response, gate result, executed substeps, contacts, terminal predicate, and failure code. MuJoCo determinism supports replay in a fixed deterministic setup, but exact reproducibility still depends on the caller controlling seeds, reset state and simulator version.
- The first physical scenario should be **one object, one target tray, one task contract, three counterfactual authorization states** (grant, deny, unknown). The model should act in all conditions without a person reviewing or approving the decision. The deny/unknown cases test refusal/gating; the grant case tests utility and erroneous refusal. A separate later family should test shared-resource allocation/fair ordering because it introduces a different oracle and should not be entangled with first-time physics integration.

### Gaps

- It is not verified whether the current Kev API accepts stable random seeds or whether all returned scores/choices are deterministic under the server’s current sampling configuration; repeatability must be measured rather than assumed from the physics engine.
- A physically meaningful contact/grasp controller and allowed grasp tolerances for the chosen MuJoCo arm are not yet implemented or calibrated.
- Simulator-truth authorization is still supplied by a synthetic task fixture, not derived from a real identity/consent authority. The synthetic register must be explicit and versioned, and the report must not claim the simulator understands ownership.

## Which minimal staged demo and evidence would show the system really runs through?

### Takeaway

Build a thin state-based tabletop demo first and postpone camera perception, broad household coverage and hardware-in-the-loop. Evidence of a completed loop requires physical object transitions under permitted actions, zero forbidden transitions after gating, and a nonzero authorized-task completion rate; prompt-only scores and symbolic graph transitions are not enough.

### Cited Findings

- Gymnasium-Robotics separates `observation`, `achieved_goal`, and `desired_goal`, and defines success through an object-to-target distance threshold; this is an example of a simulator-native terminal predicate rather than language self-report ([Fetch Pick-and-Place documentation](https://robotics.farama.org/envs/fetch/pick_and_place/)).
- Gymnasium-Robotics notes that Fetch environment reset bugs existed and were fixed in earlier versions, showing that reset semantics should be pinned and tested rather than taken for granted ([Fetch Pick-and-Place version history](https://robotics.farama.org/envs/fetch/pick_and_place/)).
- MuJoCo’s API provides deterministic computation for fixed input and explicit state reset/stepping calls, which can support replayable state-based tests ([MuJoCo Python API](https://mujoco.readthedocs.io/en/stable/python.html)).
- ManiSkill’s system-support table distinguishes CPU simulation from GPU rendering and GPU simulation; Isaac Lab’s full current workflow has substantially higher GPU and RAM requirements ([ManiSkill system support](https://maniskill.readthedocs.io/en/latest/user_guide/getting_started/installation.html); [Isaac Lab system requirements](https://isaac-sim.github.io/IsaacLab/develop/source/setup/installation/index.html)).

### Inferences

- **Milestone 0 — simulator smoke path:** pin MuJoCo and the asset revision/license; reset a fixed scene; run a no-renderer physics step; serialize state and replay it. Exit only when identical reset/command sequences produce identical goal predicates on the locked software build.
- **Milestone 1 — one physical primitive:** implement a position/IK controller from end-effector targets and gripper commands; prove the box can be physically grasped, lifted, placed in a tray, and detected as there from simulator state. A fixed scripted controller is sufficient; do not train a new policy or ask Kev to output trajectories yet.
- **Milestone 2 — typed decision loop:** request a finite choice from Kev (`inspect`, `transfer`, `wait`); validate the chosen enum, apply permission gate, run one short control segment, re-observe the actual state, and call Kev again. Record each transition. This gives the model a real role in task execution while keeping motor control independent.
- **Milestone 3 — counterfactual policy test:** evaluate at least three prompt arms—generic, token-matched neutral, PoL2—on paired identical initial states with `grant`, `deny`, and `unknown` authorization. Cross each prompt with gate disabled/enabled only inside simulation for causal decomposition. Report model forbidden-choice rate separately from physical forbidden-transition rate; also report allowed-task completion, false refusal, terminal failure, grasp drop, collision/contact violations, number of action segments, latency and recovery. `always-deny` is a diagnostic baseline, not an acceptable policy.
- **Milestone 4 — uncertainty and policy coverage:** hide one or more truth fields, provide noisy/occluded observations, and test whether Kev chooses `inspect` rather than hallucinating a permission/object fact. Only after this succeeds should the task grow to multiple objects, shared allocation, moving obstacles and richer perception; these add distinct perception, planning and social-rule confounders.
- The first demo should claim “the runtime system enforces an explicit task contract and the model’s typed choices affect a physical simulation trajectory.” It should not claim the model internally reasons in PoL2 terms, that the complete PoL2 theory is implemented, that the policy is calibrated, or that a simulated result establishes real-robot safety.

### Gaps

- No verified task-family sample size exists yet to power a general causal estimate; the current 16 handcrafted cases are not an independent benchmark and were not executed in a physics simulator.
- No camera/perception pipeline, articulated-arm controller, calibrated grasp primitive, collision threshold, or recovery behavior has been selected.
- The standard next simulator after MuJoCo depends on the question: use a more asset-rich household environment only when task diversity is limiting; use Isaac/ManiSkill only when GPU rendering/parallel simulation materially advances the next experiment. Neither ecosystem supplies PoL2 semantics by default.
