# Generic hunting classes

Every repository gets these. A class is a lens: what to look for at a
unit's surface and boundary, what a defence must show before the unit is
`covered`, and what makes a candidate. `Source:` names where the lesson is
recorded: the organization's knowledge base (`docs/en/<doc>.md#<heading>`),
an organization ADR, or — for the general know-how the organization has not
had to learn the hard way — the skill this design derives from
(`origin:<file>#<block>`, cloudflare/security-audit-skill, MIT), restated in
our words. When a product-type class refines one of these for a surface,
the unit takes the product-type class and excludes the generic one.

## Injection
Source: origin:ATTACK-CLASSES.md#Injection, security.md#Don't write a lenient parser by searching and slicing strings — make it a lexer and a small grammar, and hold its output to a contract with a property test, security.md#Read-only SQL in DuckDB: only a read-only database holds — the statement type and a READ ONLY transaction do not, security.md#ffmpeg is an interpreter — pin every input's format, and keep what it writes and reads back out of every writable place but your own

Caller-controlled text reaching an interpreter: shell, SQL, template, regex,
path grammar, format parser, log line, cache key, an external tool's
argument list. What counts as a sink depends on the product: a CLI builds
commands and paths; a service builds queries, messages and log lines; a
library processes caller data in parsers and buffers. Follow each value from
the surface to the sink, including the indirect path (a value stored
harmlessly, read back later into a context that interprets it) and the
carriers nobody escapes: a key, a field name, a header, a piece of metadata.
Covered when the sink is
reached only through an escaping or a closed vocabulary you can point at,
or when the sink itself cannot act (a read-only database, not a keyword
check or a "readonly" flag). A parser written by searching and slicing
strings is a candidate until a test pins its grammar.

## Access control
Source: origin:ATTACK-CLASSES.md#Access control, security.md#A gate asks whether the operation is allowed — "the right operation with the wrong value" passes every layer, security.md#A protected-path list is enforced per operation, not per tool family — the write tools' Block is not the read tools' protection, mcp-server-design.md#Put each control in the layer that owns it — the credential decides what can be done, the runtime what may be called, the tool only does it right

Who may do what, enforced where. A check that exists is not yet a check
that applies: which permission does it test, on which resource, and by which
mechanism? Is there a second path to the same state change that checks a weaker
permission? Can a field in the request override what the check restricts?
Does an entry authenticate but forget to authorise? Do bulk, batch, export
and import paths enforce per-item permission? List the enforcers by
operation (read / write / execute / leave the machine), never by tool
family. Covered when every path to the operation passes one named enforcer.
A gate that answers "is the operation allowed" never sees a wrong value
inside an allowed operation: say so rather than claim a layer covers it.

## Resource and file handling
Source: origin:ATTACK-CLASSES.md#Resource and file handling, security.md#Path confinement that checks a resolved path and then opens the original is a TOCTOU — make the check and the open one operation, security.md#Compare places by identity, not by name — this disk does not distinguish case, security.md#Clean up from what was created, not from what was planned — only an exclusive create's success enters the ledger, and only the ledger deletes, config-and-io.md#exec cancellation kills only the DIRECT child — a pipe-holding grandchild blocks Wait forever, security.md#Building a tree with x/net/html allocates quadratically for some inputs — cut attacker HTML down before the parser

Paths, links, archives, temporary files, child processes, limits. Path
traversal through `..`, encodings, null bytes and links; archive extraction
that writes outside its directory; deserialisation of caller data; a check
and the open it protects done as two operations on two names (a link
swapped between them escapes); two names for one place (case, Unicode form,
a hard link) defeating a string compare; cleanup that deletes what was
planned rather than what was created; a time limit that stops the child but
not the grandchild holding the pipes; reads, writes and recursion with no
bound when the input is caller-controlled, and work that grows faster than
the input (a tree builder quadratic on some HTML). Covered when the check and the
open are one operation on one file identity, places are compared by
identity, cleanup deletes only what an exclusive create recorded, and limits
reach the whole process group.

## Cryptography and secrets
Source: origin:ATTACK-CLASSES.md#Cryptography and secrets, security.md#Go's `url.Error` quotes the whole URL — a config validation error can leak a credential, security.md#An upstream API's error message can quote the credential you sent — build your own error text, security.md#A credential may follow a redirect only within the domain the request started in, security.md#A diagnostic dump is a superset of what it captures — derive its modes from the most protected thing inside, security.md#Remove your own namespace from children rather than keeping it — invert the prefix rule, and grep the org before calling a namespace yours, security.md#Never embed absolute paths in shareable artifacts' metadata, security.md#When the credential is more powerful than the use, put the restraint in the client

Two questions. Where a credential travels after it is read: error text,
logs, URLs, redirects, diagnostic dumps, child environments, artifacts meant
to leave the machine, client-visible responses. And whether the primitives
are sound: randomness for tokens, keys and nonces from a non-secret source;
hardcoded secrets; broken key derivation, missing authentication of
ciphertext, nonce or IV reuse, ECB; secret comparison that leaks timing; a
crypto failure whose error path falls back to no crypto. Covered when every
error path builds its own text, credentials are bounded to the domain they
started in, dumps take the mode of the most protected thing inside, and the
primitives are the platform's, used as documented. A credential more
powerful than the use needs its restraint in the client that holds it.

## Business logic
Source: origin:ATTACK-CLASSES.md#Business logic, config-and-io.md#A key that is present is a value that was given — do not read `""`, NaN or a sentinel as "not set", mcp-server-design.md#Discarding a type assertion on a required argument turns absence into a destructive default, mcp-server-design.md#Call-scoped state on a long-lived server must end with the call, or carry an expiry, mcp-server-design.md#Retry safety comes from a resource you named, not from a token whose meaning you assumed

The rule the code means to enforce, and the states it did not expect. For
each workflow: can a step be skipped, repeated or run backwards; what
happens when step two of three fails; do two concurrent operations produce
an invalid state (check-then-act without atomicity); do negative, zero,
maximal, NaN or coerced numbers pass; does an absent or null argument
become a destructive zero value; is an empty string or a sentinel read as
"not set"; is data from storage, config or another component trusted
because "it was validated on the way in"; what does an expiry or rate
window do at its exact boundary; what is the posture when config is
missing, a flag is off, a dependency is down, a migration is half done;
does state outlive the call it belonged to; does a retry repeat a
non-idempotent effect. Covered when each branch you traced matches the
behaviour the documentation promises and the sad paths refuse rather than
default.

## Feature abuse
Source: origin:ATTACK-CLASSES.md#Feature abuse and data leakage, security.md#Close SSRF inside the dialer as a finite address domain — resolve, judge and connect as one operation, carry no credentials, bound where a loosening setting may come from, security.md#A permission justified by "only a human writes this input" becomes a hole the moment delegation lets a model write it, config-and-io.md#A child process is told whom it serves by parameters on its launch line, never by guessing

A legitimate feature used by the wrong party, against the wrong target, or
as an oracle. Export, backup and snapshot as exfiltration above the caller's
level; import and restore as a write that skips validation or permission;
search, filter and sort as an oracle for content the caller cannot read;
error messages, timings and status codes that differ between "does not
exist" and "no access"; preview and draft tokens that unlock more than one
item; a fetcher that reaches localhost, the LAN or cloud metadata, or
follows a redirect there; an input grammar that was safe while only a human
typed it; an identity guessed from the environment instead of stated on
the launch line. Covered when each feature's reach is bounded to the
caller's authority and the fetcher resolves, judges and connects as one
operation.

## Chained
Source: origin:ATTACK-CLASSES.md#Chained vulnerabilities and trust boundaries, security.md#A guard keyed on one layer's refusal flag is a hole at every other layer — key it on "the tool ran", testing.md#When two defences cover one failure, an observation explained by either is evidence for neither

Two components that are each correct against their own contract, where the
second trusts more than the first promised. Write down the promise the
producer keeps (how long a value may be, its type, its normalisation, whose
tenant it belongs to) next to the assumption the consumer makes, and look at
the gap; follow second-order use (a stored field name
becomes a JSON path, a slug a file path, escaped text raw rendering); watch
capability growth after delegation, refresh, caching or role change; check
setup, migration, soft-delete, revoke/expiry and check/use windows; confirm
what a rollback or restore brings back. A guard keyed on one layer's signal
is bypassed by a refusal from another layer; a defence "covered" by two
mechanisms may be covered by neither. Establish each prerequisite; when one
unit's candidate depends on another unit's state, record both coverage ids.

## Wildcard
Source: origin:ATTACK-CLASSES.md#Wildcard, llm-integration.md#Subagent output contracts must state what NOT to output

Anything the other classes do not name, so that a real weakness outside the
vocabulary has a destination inside the ledger. Spend time on the code that
seems to have nothing to do with security: the strangest code and why it
exists;
half-finished, experimental, compatibility and fallback features; what the
API allows that the client never does; hidden parameters, headers and
routes; features combined that were not designed together; reverted fixes
and removed secrets in the history; assumptions about the environment (a
case-sensitive filesystem, an accurate clock, trustworthy DNS); what the
tests do not test. A wildcard candidate still needs a full trace and a
boundary; an observation without one is a note, not a finding.

## Obvious things
Source: origin:ATTACK-CLASSES.md#Obvious things, security.md#Sample placeholders must not trip secret scanning, security.md#Never write PII — "it's discoverable anyway" is not a reason, shell-scripting.md#An operational script must not infer its root from $PWD — and a skipped check must never summarize green, testing.md#A release gate that skips is a gate that passes

The elementary exposures that go unchecked because each reviewer assumes
another one covered them. Hardcoded
passwords, keys and tokens; real-looking placeholders; TODO / FIXME / HACK
comments that name a missing check; debug and dev modes reachable from an
environment variable, parameter or header; test or seed credentials that
work for real; unprotected debug, admin, health or config endpoints;
`.env`, key and credential files in the tree, and a `.gitignore` that does
not cover them; unpinned dependencies; `eval`, `exec`, dynamic import and
child processes fed dynamic input; permissive CORS and cookie flags; open
redirects; stack traces and internal paths in production errors; personal
data in documents and release notes; checks that report green when they did
not run; operational scripts that infer their root from the working
directory. Work the list to its end, item by item. A hit on the list is
not yet a finding: follow it to an affected principal and resource before it
becomes a candidate.
