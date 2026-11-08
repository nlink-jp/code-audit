# Hunting classes: Go and Python CLIs

Apply when the target is a command-line tool, including the CLI face of a
server. Its inputs are arguments, environment, config files, stdin and the
third-party data it fetches; its outputs reach terminals, files the user
owns, logs and child processes.

## Environment inherited by child processes
Source: security.md#Remove your own namespace from children rather than keeping it — invert the prefix rule, and grep the org before calling a namespace yours, config-and-io.md#A child process is told whom it serves by parameters on its launch line, never by guessing
Refines: classes/generic.md#Cryptography and secrets, classes/generic.md#Feature abuse

Every `exec`: what environment does the child get? The tool's own
namespace (session ids, tokens, work directories) passes through unless
removed, and a child that guesses whom it serves from inherited variables
serves the wrong session under nesting. Covered when one spawn function
removes the tool's own namespace — not the operator's environment, which is
left alone — and children are told whom they serve on their launch line.

## Credentials in error text
Source: security.md#Go's `url.Error` quotes the whole URL — a config validation error can leak a credential, security.md#A config decoder's syntax error quotes the token it could not parse — an unquoted key goes to stderr, security.md#An upstream API's error message can quote the credential you sent — build your own error text
Refines: classes/generic.md#Cryptography and secrets

Validation errors that quote the URL they refused, decoder errors that
quote the token they could not parse, upstream 401 bodies passed through:
each puts a credential on stderr and into logs. Covered when every error
path builds its own text; readable from source alone.

## Lenient or best-effort configuration
Source: ADR-026, config-and-io.md#Read hand-written JSON/TOML with strict decoding, config-and-io.md#After making config decoding strict, find the callers that load it best-effort, config-and-io.md#A key that is present is a value that was given — do not read `""`, NaN or a sentinel as "not set"
Refines: classes/generic.md#Business logic

Hand-written config decoded leniently hides typos as silent defaults; a
caller written as "use it if it loads" turns one bad key into a run on the
default location. A present key with an empty, NaN or sentinel value is a
given value, not "unset". Exceptions the records allow: machine-generated
data is decoded leniently on purpose, and unknown keys may be allowed in a
file shared with other readers. Covered when hand-written config is strict,
every loader fails loud, and present values are taken as given. Refines
generic `Business logic`.

## Cleanup from a plan instead of a ledger
Source: security.md#Clean up from what was created, not from what was planned — only an exclusive create's success enters the ledger, and only the ledger deletes
Refines: classes/generic.md#Resource and file handling

Failure paths that delete the paths they intended to create delete what
someone else placed there. Covered when only an exclusive create's success
enters a ledger and only the ledger deletes.

## Output replaced by rename against the user's files
Source: config-and-io.md#A CLI that builds its output in memory should write it in place, as a shell's `>` does — write-and-rename works against the user's files, config-and-io.md#Marker/flag files read by other processes must land by temp+rename (os.WriteFile is create-then-write)
Refines: classes/generic.md#Resource and file handling

Write-and-rename onto a user-named output replaces a read-only file, widens
its mode, splits hard links and swaps a link for a regular file. Exception:
files other processes read concurrently (markers, flags, shared settings)
must land by temp+rename. Covered when a user-named output is written in
place and only shared files are renamed in. Mostly a correctness lesson;
report it as a candidate only with a concrete loss of a user's file.

## Working directory inferred
Source: config-and-io.md#Read the working directory from the kernel, not `$PWD` — one directory becomes two spellings, shell-scripting.md#An operational script must not infer its root from $PWD — and a skipped check must never summarize green
Refines: classes/generic.md#Obvious things

A root taken from `$PWD` or the shell's idea of the directory differs in
spelling from the kernel's and drifts under agents whose shell persists;
operational scripts defaulting their target to the current directory run
their checks nowhere and report green. Covered when the working directory
is read from the kernel in one place and scripts derive their root from
their own location.

## Third-party text printed raw
Source: security.md#Make third-party text inert for a terminal once, over the whole result — not at each print site, security.md#Making text inert at the ingress is not enough when a transform downstream decodes — hold the transform's output to what it writes itself
Refines: classes/generic.md#Injection

Fetched descriptions, file names, headers and JSON output reach a terminal
with escape sequences and C1 controls intact, including through `--json`.
Covered when one function makes the whole output inert at the terminal
egress and downstream transforms are held to what they write themselves.
Output to a pipe or a file may stay verbatim; do not report it. Refines
generic `Injection`.

## Credential follows a redirect
Source: security.md#A credential may follow a redirect only within the domain the request started in
Refines: classes/generic.md#Cryptography and secrets

Two shapes: an `Authorization` header re-attached in a redirect hook
follows the redirect to whatever host it names; and a key carried in a
custom header (`X-Api-Key` and the like) is never stripped by the HTTP
client at all, so a default client leaks it on the first redirect. Covered
when every credentialled client either refuses to follow redirects or
bounds them to the domain the request started in.

## Diagnostic dump wider than its subject
Source: security.md#A diagnostic dump is a superset of what it captures — derive its modes from the most protected thing inside
Refines: classes/generic.md#Cryptography and secrets

Debug flags that write request bodies, transcripts or raw responses: are
the directory and file modes derived from the most protected content
inside, and is the switch documented? Covered when both hold. Refines
generic `Cryptography and secrets`.

## Checks that fail open
Source: shell-scripting.md#Tell "the input could not be fetched" apart from an empty answer, testing.md#A release gate that skips is a gate that passes, release-engineering.md#A fail-open step plus a verifier that only displays = a defective release with green checks
Refines: classes/generic.md#Obvious things

A fetch that fails is reported as an empty answer; a skipped check
summarises green; a verifier that only displays never fails the step. Look
in Makefiles, release scripts and health checks as well as in the tool
itself. Covered when a failed input is told apart from an empty one and a
skipped or display-only check cannot summarise green.

## Grandchild survives the timeout
Source: config-and-io.md#exec cancellation kills only the DIRECT child — a pipe-holding grandchild blocks Wait forever
Refines: classes/generic.md#Resource and file handling

A time limit or Ctrl+C that kills only the direct child leaves a grandchild
holding the pipes and the parent blocked. Covered when the process group is
ended and the wait is bounded.

## Parsers of third-party formats by searching and slicing
Source: security.md#Don't write a lenient parser by searching and slicing strings — make it a lexer and a small grammar, and hold its output to a contract with a property test, security.md#Go's `mime.ParseMediaType` drops every parameter when one is malformed — an attacker can hide an attachment's name, security.md#Convert 8-bit values after tokenizing — a Shift_JIS trail byte 0x5C eats a quoted-string escape and adds an address
Refines: classes/generic.md#Injection

Mail headers, media types, addresses and other formats parsed by searching
and slicing strings: one encoding converted before tokenizing adds an
address; and a strict library parser that drops every parameter when one is
malformed lets an attacker hide an attachment's name — for attacker-written
values the remedy is a parser that reads each parameter on its own. Covered
when the parser is a lexer and a small grammar pinned by a test over the
whole output contract, or, for attacker-written parameter lists, a parser
that reads each parameter on its own and drops only the malformed one.

## Credential more powerful than the use
Source: security.md#When the credential is more powerful than the use, put the restraint in the client
Refines: classes/generic.md#Cryptography and secrets

A token without scopes gives a read-only tool the power to actuate. Covered
when the write operations are not implemented at all — not hidden behind a
flag.

## Absolute paths and personal data in shared artifacts
Source: security.md#Never embed absolute paths in shareable artifacts' metadata, security.md#Never write PII — "it's discoverable anyway" is not a reason
Refines: classes/generic.md#Cryptography and secrets, classes/generic.md#Obvious things

Metadata of generated files, release notes and reports: home directories,
user names, signer names, personal names from headers. Covered when
artifacts record identifiers instead.
