# Hunting classes: Go and Python CLIs

Apply when the target is a command-line tool, including the CLI face of a
server. Its inputs are arguments, environment, config files, stdin and the
third-party data it fetches; its outputs reach terminals, files the user
owns, logs and child processes.

## Environment inherited by child processes
Source: security.md#Remove your own namespace from children rather than keeping it — invert the prefix rule, and grep the org before calling a namespace yours, config-and-io.md#A child process is told whom it serves by parameters on its launch line, never by guessing

Every `exec`: what environment does the child get? Session identifiers,
tokens and the tool's own namespace pass through unless removed. A child
that guesses whom it serves from inherited variables serves the wrong
session under nesting.

## Credentials in error text
Source: security.md#Go's `url.Error` quotes the whole URL — a config validation error can leak a credential, security.md#A config decoder's syntax error quotes the token it could not parse — an unquoted key goes to stderr, security.md#An upstream API's error message can quote the credential you sent — build your own error text

Validation errors that quote the URL they refused, decoder errors that
quote the token they could not parse, upstream 401 bodies passed through:
each puts a credential on stderr and into logs. Covered when every error
path builds its own text.

## Lenient or best-effort configuration
Source: ADR-026, config-and-io.md#Read hand-written JSON/TOML with strict decoding, config-and-io.md#After making config decoding strict, find the callers that load it best-effort, config-and-io.md#A key that is present is a value that was given — do not read `""`, NaN or a sentinel as "not set"

Hand-written config decoded leniently hides typos as silent defaults; a
caller written as "use it if it loads" turns one bad key into a run on the
default location. A present key with an empty, NaN or sentinel value is a
given value, not "unset".

## Cleanup from a plan instead of a ledger
Source: security.md#Clean up from what was created, not from what was planned — only an exclusive create's success enters the ledger, and only the ledger deletes

Failure paths that delete the paths they intended to create delete what
someone else placed there. Covered when only an exclusive create's success
enters a ledger and only the ledger deletes.

## Output replaced by rename against the user's files
Source: config-and-io.md#A CLI that builds its output in memory should write it in place, as a shell's `>` does — write-and-rename works against the user's files

Write-and-rename onto a user-named output replaces a read-only file,
widens its mode, splits hard links and swaps a link for a regular file.
Check what the destination may be and what the rename discards.

## Working directory inferred
Source: config-and-io.md#Read the working directory from the kernel, not `$PWD` — one directory becomes two spellings, shell-scripting.md#An operational script must not infer its root from $PWD — and a skipped check must never summarize green

A root taken from `$PWD` or the shell's idea of the directory differs in
spelling from the kernel's and drifts under agents whose shell persists.
Operational scripts defaulting their target to the current directory run
their checks nowhere and report green.

## Third-party text printed raw
Source: security.md#Make third-party text inert for a terminal once, over the whole result — not at each print site, security.md#Making text inert at the ingress is not enough when a transform downstream decodes — hold the transform's output to what it writes itself

Fetched descriptions, file names, headers and JSON output reach a terminal
with escape sequences and C1 controls intact, including through `--json`.
Covered when one function makes the whole output inert at the egress and
downstream transforms are held to what they write themselves.

## Credential follows a redirect
Source: security.md#A credential may follow a redirect only within the domain the request started in

An `Authorization` header re-attached in a redirect hook follows the
redirect to whatever host it names. Check every HTTP client that sets
credentials for a redirect policy bounded to the starting domain.

## Diagnostic dump wider than its subject
Source: security.md#A diagnostic dump is a superset of what it captures — derive its modes from the most protected thing inside

Debug flags that write request bodies, transcripts or raw responses: are
the directory and file modes derived from the most protected content
inside, and is the switch documented?

## Checks that fail open
Source: shell-scripting.md#Tell "the input could not be fetched" apart from an empty answer, testing.md#A release gate that skips is a gate that passes, release-engineering.md#A fail-open step plus a verifier that only displays = a defective release with green checks

A fetch that fails is reported as an empty answer; a skipped check
summarises green; a verifier that only displays never fails the step.
Look in Makefiles, release scripts and health checks as well as in the
tool itself.

## Grandchild survives the timeout
Source: config-and-io.md#exec cancellation kills only the DIRECT child — a pipe-holding grandchild blocks Wait forever

A time limit or Ctrl+C that kills only the direct child leaves a
grandchild holding the pipes and the parent blocked. Covered when the
process group is ended and the wait is bounded.

## Lenient parsers of third-party formats
Source: security.md#Don't write a lenient parser by searching and slicing strings — make it a lexer and a small grammar, and hold its output to a contract with a property test, security.md#Go's `mime.ParseMediaType` drops every parameter when one is malformed — an attacker can hide an attachment's name, security.md#Convert 8-bit values after tokenizing — a Shift_JIS trail byte 0x5C eats a quoted-string escape and adds an address

Mail headers, media types, addresses and other formats parsed by
searching and slicing: one malformed parameter hides a name, one encoding
converted before tokenizing adds an address. Covered when a lexer and
grammar are pinned by a test over the whole output contract.

## Credential more powerful than the use
Source: security.md#When the credential is more powerful than the use, put the restraint in the client

A token without scopes gives a read-only tool the power to actuate. The
defence is that the write operations are not implemented, not that they
are hidden behind a flag.

## Absolute paths and personal data in shared artifacts
Source: security.md#Never embed absolute paths in shareable artifacts' metadata, security.md#Never write PII — "it's discoverable anyway" is not a reason

Metadata of generated files, release notes and reports: home directories,
user names, signer names, personal names from headers. Record by
identifier instead.
