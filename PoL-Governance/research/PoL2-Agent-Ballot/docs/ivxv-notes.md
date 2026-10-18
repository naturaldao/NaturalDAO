# IVXV reading notes (source: github.com/valimised/ivxv, branch `published`)

Working notes taken while reading the repository on 2026-10-18. Most of the
normative documentation is in Estonian under `Documentation/public` and
`Documentation/et`; `Documentation/en` holds only the backend-log reference.
Several component READMEs (choices, proxy, storage, verification, mid,
smartid, sessionstatus, collector-admin) are empty placeholders, so the Go
source was used for those.

## Components

**Collector** (Go, JSON-RPC over TLS, routed by HAProxy on SNI):
`proxy` (stateless, never terminates TLS) · `choices` (authenticates voter,
returns district choices) · `voting` (`RPC.Vote`: session check, rate limit,
container signature, `ASN1CiphertextVerify` on each ballot, identity ==
signer, 16-byte VoteID, store, then fetch OCSP + `tspreg` qualifiers) ·
`verification` (`RPC.Verify(VoteID)`, enforces `verification.count`,
`.minutes`, `latestonly` with compare-and-swap) · `storage` (etcd in
production; get/put/prefix/CAS only) · `votesorder` + `xroad-service` (feed
to the election information system) · `mid`/`smartid`/`webeid` auth helpers
· `sessionstatus`. ID-card auth is TLS client certificates.

**collector-admin**: Apache/WSGI; loads signed command packages, tracks
collector state, exports the ballot box. Roles: admin, election-conf-manager,
viewer.

**Key application** (Java): `groupgen`, `init` (trusted dealer generates the
key in memory; shares to smart cards, M-of-N — DEMO config uses 5 of 9),
`testkey`, `decrypt` (reconstructs from a quorum, decrypts with proofs),
`util`. Signing protocol produces RSA-PSS.

**Processor** (Java): `check → squash → revoke → anonymize`.
`squash` keeps each voter's latest vote. `revoke` applies signed revoke /
restore lists (this is how paper votes cancel e-votes; there is no automatic
rule in the protocol text). `anonymize` strips voter data and signatures,
groups ciphertexts by district/station → `<id>-bb-4.json`.

**Mix-net**: external Verificatum driven by an IVXV adapter; input
`bb-4.json` + `pub.pem`, output `shuffled.json` + `proof.zip`.

**Auditor** (Java): `convert` (Verificatum I/O ↔ anonymised ballot boxes),
`mixer` (shuffle proof), `decrypt` (decryption proofs + tally consistency),
`integrity` (processor logs vs ballot boxes).

## Vote protocol

* Plaintext ballot `<ehak 4 digits>.<candidate 3–4 digits>` → group element.
* Inner envelope: ElGamal (MODP or EC), DER `IVXVElGamalCiphertext`; public
  key is X.509 SPKI with OID `id-ivxv-modp-elgamal` / `id-ivxv-ecc-elgamal`,
  parameters include the election id.
* Outer envelope: BDOC 2.1 (XAdES) container, one signature
  (`META-INF/signature0.xml`), one data file per question named
  `<election>.<question>.ballot`, SHA-256, c14n11, ecdsa-sha256. Voter app
  produces BES; collector qualifies to BDOC-TS.
* Qualification: OCSP for the signer certificate + RFC 3161 timestamp over
  the canonicalised SignatureValue. The timestamp doubles as the
  registration receipt (`tspreg`): the collector signs the MessageImprint
  and puts that signature in the TSP nonce. Abstractly
  `KORRALDUS = Sign_K(V_id, Hash(VOTE))`, `KINNITUS = Sign_R(Hash(KORRALDUS), t)`.
  After the election the TSA hands over every request whose nonce verifies
  against the collector certificate; the processor reconciles with the
  ballot box (vote-with-receipt-but-no-registration is the registrar's
  fault and is counted; registration-without-vote is the collector's fault
  and the vote must be found).
* Individual verification: voter app keeps the ElGamal randomness and
  passes VoteID + randomness via QR; verification app calls `RPC.Verify`,
  gets the signed vote + qualifiers + choices list and decodes the
  ciphertext. Limits from election config (DEMO: 3 times within 30 min,
  optional `latestonly`, `verificationstop`).
* Mixing widens each ciphertext with pseudo-ciphertexts `(1, encode(x))`
  for election/district/station/question ids; shuffle proof verified per
  the Verificatum verifier manual.
* Decryption proof: for `c=(c0,c1)`, plaintext `d`, proof `(a,b,s)`,
  challenge `k` from a DRBG seeded with DER(`"DECRYPTION"||pk||c||d||a||b`);
  check `c0^s = a·(c1/d)^k` and `g^s = b·y^k` (Chaum–Pedersen).

## Configuration

YAML in signed BDOC/ASiC-E command packages. Collector trust root
(`*.trust.yaml`: signer roots, BES/TS profile, TSP signers, `delaytime`,
`tsdelaytime`, initial admin CNs; loading it resets the collector).
Election config: identifier, questions, `period`
(servicestart/electionstart/electionstop/servicestop/verificationstop),
voting rate limits, `verification` (count/minutes/latestonly),
`voterlist.key` (ECDSA), `auth` (tls/ticket), `identity`, `age`,
`vote.bdoc`, `mid`/`smartid`, `qualification` (tspreg + ocsp), `ballot`
public key. Districts and choices are JSON (`ivxv.districts.schema`,
`ivxv.choices.schema`) in signed `.asice`; voter lists are changesets
`<n>.<id>.voters.utf` + detached ECDSA `.voters.sig`. Votes cast between
`servicestart` and `electionstart` are test votes and not tallied.

## Lifecycle

Collector states: not installed → installed (trust root + technical config)
→ configured (election config; can collect and export) ↔ partial failure
↔ failure; never back to installed. Overall: setup (trust roots, key
groupgen/init/testkey, configs, lists, authorisations) → voting (voter-list
changesets loaded) → processing (check/squash/revoke/anonymize) → mixing →
tally and audit.

## Data formats

Ballot box: Zip64 with
`votes/<voter id>/<yyyymmddhhmmssmmm±zzzz>.{version|bdoc|ocsp|tsp|tspreg}`.
Processor outputs `.check.log1`, `.squash.log2`, `.revoke.log2`,
`.anonymize.log3`, an e-voter list, and a per-district/station result
(`ivxv.result.schema`, must include invalid count and every choice even at
zero). Collector logs: JSON via rsyslog, millisecond timestamps, session id
on every entry, sensitive values hashed, optional Guardtime integrity.

## Files consulted

`Documentation/public/protokollid/{02,04,05,06,06a,07,08,09,11,12}-*.rst`,
`Documentation/public/arhitektuur/kogumisteenus.rst`,
`Documentation/et/seadistuste_koostejuhend/*`,
`Documentation/et/votmerakendus/votmeosakute_protokollid.rst`,
`Documentation/et/kasutusmall/*`, `Documentation/et/example-config/*`,
`common/schema/*`, `common/collector/conf/conf.go`,
`voting/service/voting/main.go`, `verification/service/verification/main.go`,
`{auditor,key,processor,voting}/README.rst`.

License of IVXV: see its `LICENSE` (copyright Estonian State Electoral
Office; created by Cybernetica AS). This repo contains no IVXV code.
