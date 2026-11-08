# Hunting classes: MCP servers

Apply when the target speaks MCP (stdio or HTTP). The server's callers are
models, its arguments are model-written, and its results and descriptions
are read by a model: every class below treats the tool boundary as a trust
boundary in both directions. A server's CLI face is hunted with `cli.md`.

## Path confinement checked then reopened
Source: security.md#Path confinement that checks a resolved path and then opens the original is a TOCTOU — make the check and the open one operation, security.md#Rewrite a path typed through a link outside the roots once, where the call comes in — when the verdict and the run each resolve it, a swap in between gets past the verdict, security.md#Canonicalizing a path to the kernel's name needs the right open, the right link test, and a re-check after the open

For each path argument: is the judged identity the opened identity? A
lexical check plus a separate resolve, or a verdict and a run that each
resolve the name, leaves a window a link swap uses. Covered by any one of
the recorded remedies: the open goes through a rooted handle that refuses
to leave the root; the typed path is rewritten once where the call comes in
and only that result is used; or the opened descriptor's kernel name is
read back and re-checked after the open. Refines generic
`Resource and file handling` for this surface.

## Writes outside the declared work directory
Source: ADR-021, ADR-022, mcp-server-design.md#If you return a file, the output root is a per-call argument, not a startup flag, security.md#A check that refuses places must not write to test them — ask access(2) whether a directory is writable, security.md#ffmpeg is an interpreter — pin every input's format, and keep what it writes and reads back out of every writable place but your own

Every write the server performs: is its destination the per-call work
directory (or a directory validated beneath it), never a startup default or
the server's own tree? Is `<work_dir>/<workspace_id>` itself judged, not
only `work_dir`? A writability probe that creates a file is a write outside
the contract. Exception the record allows: a server's own intermediate
files in a per-job directory under the user's cache directory, never
`$TMPDIR`. Whether the validated directory refuses a credential location at
runtime is readable when the server uses the organization's path library;
otherwise it is `needs_validation`.

## Places compared by name
Source: security.md#Compare places by identity, not by name — this disk does not distinguish case, ADR-022

A refused location (credential stores, the server's own directory, the
runtime's config) compared as a string passes another spelling on a
case-insensitive, Unicode-normalising disk and passes a hard link. Covered
only when the comparison is by file identity **and** by the folded kernel
name, both, every time — the organization's path library does this; a
home-grown comparison is a candidate until it shows both. Refines generic
`Resource and file handling`.

## Server-authored text passed on as fact
Source: security.md#Tool descriptions are the one server-authored text you cannot wrap — quarantine them with on-request advertisement and a "librarian", security.md#Server-authored metadata can be evidence for an LLM judge — as a claim, never a fact

Where this server forwards text another server or an upstream wrote: a
proxy or aggregator that passes other servers' tool descriptions through
unwrapped, a result that presents an upstream's prose, file names or
annotations as the server's own statement. Covered when forwarded
descriptions are quarantined (advertised on request, not pasted into every
session) and third-party text in results is marked as such. Do not rewrite
MCP result data to make it inert — that changes what the model receives;
the mark, not the mutation, is the remedy.

## Sandbox-writable directory read from the host
Source: security.md#A directory the sandbox can write is input: reach it through an `os.Root`, opened from the directory someone vouched for

When model-written code runs in a container or subprocess with a shared
directory, every host-side read of that directory is a read of attacker
input: a planted link points wherever the code chose, a FIFO blocks the
reader. Covered only when the host opens through a rooted handle that
refuses links and rejects anything that is not a regular file before
reading.

## Required argument absent becomes a destructive default
Source: mcp-server-design.md#Discarding a type assertion on a required argument turns absence into a destructive default, mcp-server-design.md#Clients pre-validate inputSchema.enum — keep server-side validation anyway

The schema's `required` list binds the client, not the handler. For each
destructive tool: what does a missing, null or mistyped argument execute
as? Empty string as "delete", zero as "unbounded", false as "skip the
check" are candidates. Covered when the handler checks presence and type
itself before acting. Refines generic `Business logic`.

## Credential or control text leaks through the protocol
Source: security.md#A config decoder's syntax error quotes the token it could not parse — an unquoted key goes to stderr, security.md#An upstream API's error message can quote the credential you sent — build your own error text, security.md#Go's `url.Error` quotes the whole URL — a config validation error can leak a credential, mcp-server-design.md#stdio servers embedding native libraries must isolate stdout at the fd level, mcp-server-design.md#Don't expose internal IDs in tool results

Error text travels into the client's logs and the model's context. Does any
error quote config input, URLs with userinfo, or upstream messages
verbatim? Does anything other than JSON-RPC write to fd 1 on a stdio
server? Does a result carry an identifier or credential the follow-up call
does not need? Covered when every error path builds its own text, fd 1 is
isolated at the descriptor level, and results carry only what the next call
uses. Refines generic `Cryptography and secrets`.

## State that outlives the call
Source: mcp-server-design.md#Call-scoped state on a long-lived server must end with the call, or carry an expiry, mcp-server-design.md#Never cache live account state

A server lives for days. Rate-limit memory, caches of the account's own
configuration, per-call paths kept on the engine: each becomes a cross-call
leak or a stale answer presented as current. Name the lifetime of every
mutable field; covered when each ends with its call or carries an expiry,
and the account's own state is never cached. Refines generic
`Business logic`.

## Child process not stopped
Source: config-and-io.md#exec cancellation kills only the DIRECT child — a pipe-holding grandchild blocks Wait forever, mcp-server-design.md#A synchronous write to a child's stdin is unbounded — outside the deadline, one wedged peer stalls everything, mcp-server-design.md#MCP's cancellation notification may be ignored by the receiver — killing the child process is still the only reliable stop

Cancellation and time limits on the server's own children: is the whole
process group ended, or only the direct child while a grandchild holds the
pipes? Is a write to a child's stdin inside the deadline, or can one wedged
peer stall every client? Covered when the group is killed, the wait is
bounded, and writes to children are under the same deadline. Refines
generic `Resource and file handling`.

## Control placed in the wrong layer
Source: mcp-server-design.md#Put each control in the layer that owns it — the credential decides what can be done, the runtime what may be called, the tool only does it right, mcp-server-design.md#Enumerate the capability surface before building a control layer

A tool-side mode switch, confirmation dance or hidden tool that tries to
hold back what the credential already allows is not a defence; it is
complexity a model can route around. Record it as a hardening note unless a
concrete bypass exists, and check that the credential's scope matches the
server's declared purpose. Refines generic `Access control`.

## Read-only SQL that is not
Source: security.md#Read-only SQL in DuckDB: only a read-only database holds — the statement type and a READ ONLY transaction do not

Model-written SQL meant to read only: a keyword check, a statement-type
check or a READ ONLY transaction each let a write through. Covered only
when the database itself is opened read-only. Refines generic `Injection`.
