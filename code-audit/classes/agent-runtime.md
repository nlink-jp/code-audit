# Hunting classes: LLM agent runtimes

Apply when the target runs a model that calls tools. The model is a party
inside the trust boundary that an attacker can address through any text the
model reads; the operator's typed words are the one channel the attacker
cannot write. Several bars below name a runtime fact (whether a cage holds,
what a resolver answers); when reading cannot settle it, the candidate is
`needs_validation` with that exact fact as the blocker.

## Self-approval
Source: security.md#Self-approval is not a defence — never let the party that proposed an action approve it, security.md#Give LLM auto-approval the operator's instruction as alignment evidence

Who judges a proposed action? If a model evaluator judges the main model's
proposals, is it the same party, and does it see the operator's instruction
as evidence? A "needs review" tier answered by the proposer is no tier. A
policy the operator configured in advance is a different thing and is not
self-approval. Refines generic `Access control`.

## Guard keyed on one layer's refusal flag
Source: security.md#A guard keyed on one layer's refusal flag is a hole at every other layer — key it on "the tool ran"

Guards that key on an error prefix or a gate's denial flag miss a refusal
produced by another layer (a hook, a sandbox). Covered when the guard keys
on "the tool actually ran". Refines generic `Chained`.

## Agent-writable persistent memory
Source: security.md#Agent-writable persistent memory is a persistence vector for injection — put the trust boundary on the write, security.md#The persistence boundary is a class of files, not one tool — instruction and configuration files are memory too

Anything the model can write that a later session reads: memory stores,
instruction files, hooks, project config, skill files, `.git` internals —
through file tools and through shell redirects alike. Is the write judged
by someone other than the proposer? Is the class of files complete, or is
only the memory tool gated? Covered when every route to every such file
passes a judge that is not the proposer.

## Permission justified by a human-only input
Source: security.md#A permission justified by "only a human writes this input" becomes a hole the moment delegation lets a model write it

Find each premise of the form "only the operator types this" and each later
feature (a child agent, a pipe, a resume) that lets a model write the same
input. The premise's failure is the finding. Refines generic
`Feature abuse`.

## A loosening constraint is a permission
Source: security.md#A constraint derived from conversation may only ever tighten — one that can loosen is a permission, security.md#State the operator's intent to a judge, not the control — otherwise the model tells the user something false

Constraints derived from prose by a model may only tighten; any path by
which a derivation, a summary or a mode switch widens what is allowed is a
permission nobody granted. And what a judge is told must be the operator's
intent, not the control that enforces it — otherwise the model explains a
refusal with something false. Covered when derivations only tighten and
the judge sees intent.

## Piped input in the instruction channel
Source: security.md#Keep piped stdin out of an LLM agent's instruction channel — carry it on the data lane, security.md#The only "history" safe to feed a judge is what the operator typed — provenance splits it three ways

Does stdin, a file reference or a resumed history join the operator's typed
words in the channel a judge trusts? Covered when provenance splits
operator-typed, model-authored and fetched text, and only the first is
alignment evidence.

## Shell bounded by text rules
Source: security.md#Bound an agent's shell with the kernel's cage, not with text rules — a declaration selects a cage, a rule can only escalate

A regex or tokenizer deciding that a command is safe is bypassed by the
next spelling. Covered only when a kernel-level cage bounds the shell and
rules can only escalate, never permit. Whether the cage holds at runtime is
not readable: a profile in source makes the candidate `needs_validation`
with "confinement verified on the host" as the blocker, not `covered`.
Refines generic `Injection`.

## Protected-path list enforced per tool family
Source: security.md#A protected-path list is enforced per operation, not per tool family — the write tools' Block is not the read tools' protection

Enumerate the enforcers of each credential or persistent-file list by
operation. A list the write tools honour and the read tools do not is a read
of every secret in it. Refines generic `Access control`.

## Server-authored text unwrapped
Source: security.md#Tool descriptions are the one server-authored text you cannot wrap — quarantine them with on-request advertisement and a "librarian", security.md#A model's account of its own safety mechanisms is not a spec — it absorbs connected servers' self-descriptions as its own layers, security.md#Server-authored metadata can be evidence for an LLM judge — as a claim, never a fact

Tool results may be nonce-wrapped while tool descriptions sit in the prompt
unwrapped on every round. Where does server-authored text enter, and is any
of it treated as a description of the runtime's own defences? Giving a
judge the server's metadata as a marked claim is the recorded remedy, not a
candidate. Covered when descriptions are quarantined and every
server-authored input to a judge is marked as a claim.

## Compaction summary trusts tool output
Source: llm-integration.md#Treat a history-compaction summary as summarising untrusted data

The summariser reads a transcript full of fetched text. Does it have tools?
Is the transcript isolated as data? Covered when the summarising call has
no tools and the transcript is wrapped as untrusted data.

## Sub-agent contract without negative space
Source: llm-integration.md#Subagent output contracts must state what NOT to output, llm-integration.md#Narrow child-agent delegation to read-only, single-purpose, llm-integration.md#Don't assign write tasks to background agents

Child agents with open task arguments, write access or an output contract
that says only what to report. Covered when the child is read-only and
single-purpose and the contract gives out-of-scope observations a
destination.

## Right operation, wrong value
Source: security.md#A gate asks whether the operation is allowed — "the right operation with the wrong value" passes every layer

An injection that dictates a wrong value into the legitimate file passes
sandbox, path lists and approval alike; no mechanism covers it. Covered
when the design document names the operational control that does (a diff
review by the operator before the result is used); otherwise a `hardening`
note that says so — never a candidate against a layer that cannot see it.
Refines generic `Access control`.

## Fetch tool reaches the wrong network
Source: security.md#Close SSRF inside the dialer as a finite address domain — resolve, judge and connect as one operation, carry no credentials, bound where a loosening setting may come from

URL fetchers that judge the hostname and let the HTTP client resolve again,
that follow redirects into private ranges, or that carry credentials.
Covered when the dialer resolves, judges and connects as one operation,
carries no credentials, and any setting that loosens the address domain can
come only from the operator's own configuration, never from a project file
or the environment. What a resolver answers is a runtime fact. Refines
generic `Feature abuse`.

## Trust pinned to a directory name
Source: security.md#Pin an agent's trust to content, not to a directory name — digest with the loader's eyes, and re-pin only the one write the operator saw

Project trust, allowlists or instruction files keyed by path are inherited
by whatever content later appears at that path. Covered when trust is
pinned to a digest of what the loader reads and re-pinned only for the one
write the operator saw.

## Model output reaches the terminal raw
Source: security.md#Making text inert at the ingress is not enough when a transform downstream decodes — hold the transform's output to what it writes itself

Replies, thoughts, tool arguments and approval dialogs carrying escape
sequences set titles, write the clipboard, hide the command the operator is
approving. Covered when every string is made inert at the UI's ingress and
transforms downstream are held to their own output. Refines generic
`Injection`.

## Shared toolchain caches from a sandboxed lane
Source: security.md#Point toolchain caches inside the sandbox at the session scratch — a shared cache is a poisoning route from an unattended lane

Build and test caches shared between an unattended lane and the operator's
own builds are a poisoning route. Covered when the unattended lane's
caches point at its own scratch, apart from the approved lane's.

## Unattended degradation
Source: security.md#With no human present, degrade "ask the human" to "deny with the reason" — do not kill the ladder, security.md#A human confirmation step is not a durable boundary for granting standing permissions

In one-shot or background modes, what does "ask the human" become? And does
a one-time confirmation grant a standing permission that outlives the
context it was judged in? Covered when the unattended mode denies with the
reason instead of removing the ladder, and standing permissions are not
granted through a one-time confirmation.

## Forbidden tool refused instead of absent
Source: llm-integration.md#A tool the model must not use is made absent by name — not refused, absent; declarations were nine tenths of the prompt

A tool the model must never use that is declared and refused at call time
stays in the prompt as a temptation and an injection target. The recorded
remedy is to not declare it — and the record itself calls this prompt
shaping, not confinement: its absence is a `hardening` note, not a
candidate.
