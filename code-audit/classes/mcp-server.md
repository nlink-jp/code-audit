# Hunting classes: MCP servers

Apply when the target speaks MCP (stdio or HTTP). The server's callers are
models, its arguments are model-written, and its results and descriptions
are read by a model: every class below treats the tool boundary as a
trust boundary in both directions.

## Path confinement checked then reopened
Source: security.md#Path confinement that checks a resolved path and then opens the original is a TOCTOU — make the check and the open one operation, security.md#Rewrite a path typed through a link outside the roots once, where the call comes in — when the verdict and the run each resolve it, a swap in between gets past the verdict, security.md#Canonicalizing a path to the kernel's name needs the right open, the right link test, and a re-check after the open

For each path argument: is the judged identity the opened identity? A
lexical check plus a separate resolve, or a verdict and a run that each
resolve the name, leaves a window a link swap uses. Covered only when the
open follows no link or the check reads the kernel's name of the opened
descriptor.

## Writes outside the declared work directory
Source: ADR-021, ADR-022, mcp-server-design.md#If you return a file, the output root is a per-call argument, not a startup flag, security.md#A check that refuses places must not write to test them — ask access(2) whether a directory is writable

Every write the server performs: is its destination the per-call work
directory (or a directory validated beneath it), never a startup default,
a temp directory or the server's own tree? Is `<work_dir>/<workspace_id>`
itself judged, not only `work_dir`? A writability probe that creates a
file is a write outside the contract.

## Places compared by name
Source: security.md#Compare places by identity, not by name — this disk does not distinguish case, ADR-022

A refused location (credential stores, the server's own directory, the
runtime's config) compared as a string passes another spelling on a
case-insensitive, Unicode-normalising disk and passes a hard link. Covered
only when the comparison is by file identity or by the kernel's name.

## Server-authored text treated as fact
Source: security.md#Server-authored metadata can be evidence for an LLM judge — as a claim, never a fact, security.md#Tool descriptions are the one server-authored text you cannot wrap — quarantine them with on-request advertisement and a "librarian"

Upstream responses, file names, third-party descriptions and the server's
own annotations flow into results a model reads. Is third-party text
marked as such, or does the result present it as the server's own
statement? Does a proxy or aggregator forward another server's
descriptions unwrapped?

## Sandbox-writable directory read from the host
Source: security.md#A directory the sandbox can write is input: reach it through an `os.Root`, opened from the directory someone vouched for

When model-written code runs in a container or subprocess with a shared
directory, every host-side read of that directory is a read of attacker
input: a planted link points wherever the code chose. Covered only when
the host opens through a rooted handle that refuses links.

## Required argument absent becomes a destructive default
Source: mcp-server-design.md#Discarding a type assertion on a required argument turns absence into a destructive default, mcp-server-design.md#Clients pre-validate inputSchema.enum — keep server-side validation anyway

The schema's `required` list binds the client, not the handler. For each
destructive tool: what does a missing, null or mistyped argument execute
as? Empty string as "delete", zero as "unbounded", false as "skip the
check" are findings.

## Credential or control text leaks through the protocol
Source: security.md#A config decoder's syntax error quotes the token it could not parse — an unquoted key goes to stderr, security.md#An upstream API's error message can quote the credential you sent — build your own error text, mcp-server-design.md#stdio servers embedding native libraries must isolate stdout at the fd level

Error text travels into the client's logs and the model's context. Does
any error quote config input, URLs with userinfo, or upstream messages
verbatim? Does anything other than JSON-RPC write to fd 1 on a stdio
server? Does a result carry a credential the follow-up call does not need?

## State that outlives the call
Source: mcp-server-design.md#Call-scoped state on a long-lived server must end with the call, or carry an expiry, mcp-server-design.md#Never cache live account state

A server lives for days. Rate-limit memory, caches of the account's own
configuration, per-call paths kept on the engine: each becomes a
cross-call leak or a stale answer presented as current. Name the lifetime
of every mutable field.

## Child process not stopped
Source: mcp-server-design.md#MCP's cancellation notification may be ignored by the receiver — killing the child process is still the only reliable stop, config-and-io.md#exec cancellation kills only the DIRECT child — a pipe-holding grandchild blocks Wait forever

Cancellation and time limits: is the whole process group ended, or only
the direct child while a grandchild holds the pipes? An unbounded
synchronous write to a child's stdin stalls the server for every client.

## Control placed in the wrong layer
Source: mcp-server-design.md#Put each control in the layer that owns it — the credential decides what can be done, the runtime what may be called, the tool only does it right, mcp-server-design.md#Enumerate the capability surface before building a control layer

A tool-side mode switch, confirmation dance or hidden tool that tries to
hold back what the credential already allows is not a defence; it is
complexity a model can route around. Record it as a hardening note unless
a concrete bypass exists, and check that the credential's scope matches
the server's declared purpose.

## Third-party text reaches a terminal or log raw
Source: security.md#Make third-party text inert for a terminal once, over the whole result — not at each print site

Where the server also has a CLI face or writes logs: escape sequences and
C1 controls in upstream text reach a terminal. Covered only when one
function makes the whole result inert at the egress, not per print site.
