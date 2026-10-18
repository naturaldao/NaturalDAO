# Related work

This project sits where three literatures meet. Each gives it something, and
each leaves a gap that motivates the design.

| Literature | What it gives this project | What it leaves open |
|---|---|---|
| Jury theorems and information cascades | Why independent votes aggregate evidence and why visible votes stop doing so | Assumes independence or models its loss; says nothing about how to enforce it |
| Verifiable electronic voting | Tested protocols for secret, receipted, auditable ballots | Designed for human voters, where secrecy must last forever because of coercion |
| Multi-agent language-model decision-making | Evidence that voting, not discussion, carries most of the gains, and that models conform to visible peers | Aggregation is done in an orchestrator's memory; no eligibility, sealing, receipts or third-party audit |

The contribution here is narrow: take the second literature's machinery,
apply it to the third literature's voters, and use the first literature to
predict and check what changes.

Keys in square brackets refer to [references.bib](references.bib).

## 1. Jury theorems and information cascades

**Condorcet's jury theorem** [condorcet1785] states that if each voter is
right with probability p > 1/2 and votes independently, the probability that
the majority is right increases with the number of voters and tends to one.
Our sealed condition is a direct instance; `theory.condorcet` computes the
probability exactly and the simulations match it.

The theorem's weak point is independence. **Ladha** [ladha1992] shows that
positively correlated votes reduce the gain from adding voters. Language-model
agents built on the same base model are correlated even when sealed, so the
gains in experiment 1 are an upper bound for real agents. **Yang et al.**
[yang2024llmvoting] report that LLM votes are sensitive to presentation order
and less diverse than human votes, which is the same concern in empirical
form. **Austen-Smith and Banks** [austensmith1996] add that sincere voting is
not always an equilibrium even with independent signals; our scripted agents
vote sincerely by construction, and real agents need not.

When votes are cast in sequence and are visible, independence fails in a
specific way. **Bikhchandani, Hirshleifer and Welch** [bikhchandani1992] and
**Banerjee** [banerjee1992] show that once the public record leads by enough,
rational agents ignore their own signal, so later votes carry no new
information (an *information cascade*). With symmetric binary signals the
threshold is a lead of two, which is the rule our conformist agents follow;
`theory.cascade` computes the resulting accuracy exactly. The predicted
plateau, where adding agents no longer helps, is what experiment 1 shows.
**Anderson and Holt** [andersonholt1997] reproduce cascades with human
subjects in the laboratory, and **Ali and Kartik** [alikartik2012] show that
herding survives even when all voters share the same objective, which is our
setting: every agent wants the correct decision.

A counterpoint matters for interpretation. **Dekel and Piccione**
[dekel2000] prove that with fully rational, strategic voters, sequential and
simultaneous voting have the same equilibria. The gap we measure therefore
comes from agents that follow visible majorities (boundedly rational or
sycophantic behaviour), not from sequencing as such. Sealing is a defence
against that behaviour, and it costs nothing when agents are fully rational.

## 2. Deliberation and consensus

The consensus mode is the **Delphi method** [dalkey1963]: anonymous rounds
with controlled feedback between them. **Rowe and Wright** [rowe1999] review
its evaluation and separate two effects that are easy to confuse:
convergence of opinions across rounds and improvement in accuracy. Our
experiment 2 shows the same separation. Unanimity is reached in two rounds,
but its accuracy equals that of a single sealed majority vote, because the
second round can only re-aggregate first-round evidence. **DeGroot**
[degroot1974] gives the classic linear model of consensus under repeated
disclosure; our deliberative agents are a limiting case that adopts the
first-round majority in one step.

## 3. Verifiable electronic voting

The protocol structure follows **IVXV**, the Estonian internet voting system.
**Heiberg, Martens, Vinkel and Willemson** [heiberg2016] describe the design
that introduced the registration service, receipts and the verification
application. **Springall et al.** [springall2014] analysed the earlier
Estonian system and argued that it placed too much trust in servers and
procedures, which is one reason this project's auditor receives only the
exported record. **Kubjas, Pikma and Willemson** [kubjas2017] revisit
individual verification, and **Zhang, Li and Willemson** [zhang2021ivxv]
give a formal model of IVXV in the universal composability framework. They
note that few human voters verify their ballots; every agent can.

The cryptographic building blocks are standard. Threshold key sharing is
**Shamir**'s scheme [shamir1979]. IVXV and ElectionGuard prove correct
decryption with **Chaum–Pedersen** proofs [chaum1992] and anonymise ballots
with verifiable shuffles such as **Wikström**'s [wikstrom2009] in the
Verificatum mix-net. We replace both with publication of the key after the
close, which gives the same guarantee against misreported decryption but ends
ballot secrecy, a choice discussed in [design.md](design.md#4-what-is-deliberately-different-secrecy-ends-at-the-close).

**Helios** [adida2008] introduced open-audit voting on the web, and
**Belenios** [cortier2019belenios] adds voter credentials against ballot
stuffing, the closest academic analogue of our signed roster plus signed
envelopes. **ElectionGuard** [benaloh2024electionguard] is an open
specification with guardian key ceremonies and decryption proofs; it is the
natural upgrade path if lasting secrecy is ever needed. **Benaloh**'s
cast-or-challenge audit [benaloh2007] would let an agent harness spot-check
that an envelope encodes the intended ballot. **Bernhard et al.**
[bernhard2017] frame the tension between public evidence and ballot secrecy;
our design takes the public-evidence end of that trade-off, which is
defensible for software agents that cannot be coerced the way people can.
Because ballots become public, a full recount is cheap and risk-limiting
audits [lindeman2012] are not needed.

## 4. Governance voting on blockchains

Three deployed designs are close to this one. **Shutter**'s shielded voting
on Snapshot [shutter2022] threshold-encrypts DAO votes and reveals them after
the close, the same "secret until close, then public" policy, adopted
explicitly to stop bandwagoning during the vote. **MACI** [buterin2019maci]
lets a later key-change message invalidate earlier votes, the on-chain
counterpart of IVXV re-voting, but keeps votes private permanently.
**Open Vote Network** [mccorry2017] is self-tallying and needs no key holders,
an alternative to our custodians for small committees.

## 5. Multi-agent language-model decision-making

Majority voting over independent samples, **self-consistency**
[wang2023selfconsistency], is the single-model version of our sealed
condition, and **Li et al.** [li2024moreagents] show accuracy rising with the
number of agents under sampling-and-voting, an empirical Condorcet curve.
**Schoenegger et al.** [schoenegger2024silicon] find that aggregated LLM
forecasts rival human crowds.

Debate frameworks instead let agents read each other's answers over rounds
[du2024debate; liang2024mad; chen2024reconcile]. Two recent papers isolate
the decision rule. **Choi, Zhu and Li** [choi2025debatevote] find that
majority voting accounts for most of the gains attributed to debate and show
theoretically that debate alone does not raise expected correctness.
**Kaesberg et al.** [kaesberg2025voting] compare seven decision protocols and
find voting better on reasoning tasks (+13.2%) and consensus better on
knowledge tasks (+2.8%). Both support treating the vote as the core primitive
and consensus as an optional procedure on top, which is how this repository
is organised.

Conformity is documented directly. **Sharma et al.** [sharma2024sycophancy]
show that RLHF-trained models defer to stated views. **Weng, Chen and Wang**
[weng2025conformity] measure LLM conformity under majority pressure with the
BenchForm benchmark; **Zhang et al.** [zhang2024socialpsych] report
conformity in agent societies; and **Cho, Guntuku and Ungar** [cho2025herd]
find that herding depends on the confidence gap between an agent and its
peers and on how peer answers are presented. **Estornell and Liu**
[estornell2024multillm] model debate among similar models converging on
shared, possibly wrong, beliefs. Together these predict that open
sequential voting among real language-model agents will show the cascade
mechanism of experiment 1; `experiments/llm_herding.py` is the test.

Finally, **Conitzer et al.** [conitzer2024socialchoice] argue that social
choice theory should guide AI alignment when aggregating human feedback.
This project applies the same theory one level down, with agents as the
voters.

## Where this project differs

- **Enforcement, not instruction.** Debate papers ask agents to think
  independently. Here, independence is enforced: an agent cannot read another
  ballot before the close, because it is encrypted to a key nobody holds.
- **Third-party verifiability.** Multi-agent frameworks aggregate votes inside
  the orchestrator. Here, anyone holding the exported record can recompute
  every step, and the tests show tampering is caught.
- **Secrecy that ends.** Electronic voting keeps ballots secret forever.
  Here, ballots open at the close, so each decision carries the reasons of
  every agent, as PoL2's governance protocol requires.
- **Exact baselines.** Every simulated probability has an exact counterpart
  (`theory.py`), so the experiments test the implementation, not only the
  idea.
