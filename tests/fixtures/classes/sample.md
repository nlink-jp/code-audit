# Sample hunting classes (fixture)

## Path confinement after resolution
Source: security.md#Path confinement that checks a resolved path and then opens the original is a TOCTOU

Trace every path argument from the entry point to the open call. Confirm
the check and the open use the same file identity.

## Writes outside the declared work directory
Source: ADR-021, security.md#A check that refuses places must not write to test them

Find every write and compare its destination with the work_dir contract.

## Borrowed injection lens
Source: origin:ATTACK-CLASSES.md#Injection, security.md#A check that refuses places must not write to test them

Trace the caller's value to the sink; written in our words from the origin's lens.

```text
## not a class heading: inside a fence
```
