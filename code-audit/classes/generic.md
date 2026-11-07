# Generic hunting classes

Every repository gets these. A class is a lens: what to look for at a
unit's surface and boundary, and what a defence must show before the unit
is `covered`. `Source:` names where the lesson is recorded (knowledge
`docs/en/<doc>.md#<heading>` or an organization ADR).

## Injection
Source: security.md#Don't write a lenient parser by searching and slicing strings — make it a lexer and a small grammar, and hold its output to a contract with a property test, security.md#Read-only SQL in DuckDB: only a read-only database holds — the statement type and a READ ONLY transaction do not, security.md#ffmpeg is an interpreter — pin every input's format, and keep what it writes and reads back out of every writable place but your own

Caller-controlled text reaching an interpreter: shell, SQL, template,
regex, path grammar, a format parser, an external tool's argument list.
Follow each value from the surface to the sink and name the escaping or
the closed vocabulary that stops it. A keyword prefix check, a statement
type check or a "readonly" flag is not a defence until the sink itself is
shown unable to write; a hand-written tokenizer is a finding until a test
pins its grammar.

## Access control
Source: security.md#A gate asks whether the operation is allowed — "the right operation with the wrong value" passes every layer, security.md#A protected-path list is enforced per operation, not per tool family — the write tools' Block is not the read tools' protection, mcp-server-design.md#Put each control in the layer that owns it — the credential decides what can be done, the runtime what may be called, the tool only does it right

Who may do what, enforced where. For every privileged operation list the
enforcers by operation (read / write / execute / leave the machine), not by
tool family, and check that each path to the operation passes one. A gate
that answers "is the operation allowed" never sees a wrong value inside an
allowed operation: say so instead of claiming a layer covers it.

## Resource and file handling
Source: security.md#Path confinement that checks a resolved path and then opens the original is a TOCTOU — make the check and the open one operation, security.md#Compare places by identity, not by name — this disk does not distinguish case, security.md#Clean up from what was created, not from what was planned — only an exclusive create's success enters the ledger, and only the ledger deletes, config-and-io.md#exec cancellation kills only the DIRECT child — a pipe-holding grandchild blocks Wait forever

Paths, links, temporary files, child processes, limits. A path check and
the open it protects must be one operation on one file identity; two
names for one place (case, Unicode form, a link) defeat a string compare.
Cleanup deletes only what an exclusive create recorded. A time limit must
reach the whole process group. Unbounded reads, writes and recursion are
findings when the input is caller-controlled.

## Cryptography and secrets
Source: security.md#Go's `url.Error` quotes the whole URL — a config validation error can leak a credential, security.md#An upstream API's error message can quote the credential you sent — build your own error text, security.md#A credential may follow a redirect only within the domain the request started in, security.md#A diagnostic dump is a superset of what it captures — derive its modes from the most protected thing inside

Where a credential travels after it is read: error text, logs, URLs,
redirects, dumps, child environments, artifacts meant to leave the
machine. Weak or home-made primitives, unauthenticated encryption,
comparisons that leak timing, randomness from a non-secret source. A
credential that is more powerful than the use needs restraint in the
client that holds it.

## Business logic
Source: config-and-io.md#A key that is present is a value that was given — do not read `""`, NaN or a sentinel as "not set", mcp-server-design.md#Discarding a type assertion on a required argument turns absence into a destructive default, mcp-server-design.md#Call-scoped state on a long-lived server must end with the call, or carry an expiry

The intended rule written in the code, and the states it did not expect:
an absent or null argument that becomes a destructive zero value, an
empty string or NaN read as "not set", a sentinel that is also a valid
input, state that outlives the call it belonged to, a retry that repeats
a non-idempotent effect. Compare each branch with the behaviour the
documentation promises.

## Feature abuse
Source: security.md#Close SSRF inside the dialer as a finite address domain — resolve, judge and connect as one operation, carry no credentials, bound where a loosening setting may come from, security.md#A permission justified by "only a human writes this input" becomes a hole the moment delegation lets a model write it, config-and-io.md#A child process is told whom it serves by parameters on its launch line, never by guessing

A legitimate feature used by the wrong party or against the wrong target:
a fetcher that reaches localhost, the LAN or cloud metadata; an input
grammar that was safe while only a human typed it; an identity guessed
from the environment instead of stated on the launch line. Ask who can
reach each feature and what the feature can reach.

## Chained
Source: security.md#A guard keyed on one layer's refusal flag is a hole at every other layer — key it on "the tool ran", testing.md#When two defences cover one failure, an observation explained by either is evidence for neither, testing.md#A gate that cannot name the layer it observes has only proved the layer below

Two or more weaknesses that are each tolerable and together are not. A
guard keyed on one layer's signal is bypassed by a refusal from another
layer; a defence "covered" by two mechanisms may be covered by neither.
When one unit's candidate depends on another unit's state, record both
coverage ids on the candidate.

## Wildcard
Source: llm-integration.md#Subagent output contracts must state what NOT to output, testing.md#A gate that cannot name the layer it observes has only proved the layer below

Anything the other classes do not name. This class exists so that a real
weakness outside the vocabulary has a destination inside the ledger
instead of being dropped or mislabelled. A wildcard candidate must still
carry a full trace; an observation without one is a note, not a finding.

## Obvious things
Source: security.md#Sample placeholders must not trip secret scanning, security.md#Never write PII — "it's discoverable anyway" is not a reason, shell-scripting.md#An operational script must not infer its root from $PWD — and a skipped check must never summarize green, testing.md#A release gate that skips is a gate that passes

Committed secrets and real-looking placeholders, personal data in
documents and release notes, debug toggles and verbose modes left on,
checks that report green when they did not run, operational scripts that
infer their root from the working directory. Cheap to look for; look for
them in every repository before the subtle classes.
