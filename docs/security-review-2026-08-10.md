# Security and hardening review — 2026-08-10

A read of the whole repository against its own non-negotiables, done at the
mid-point of Sprint 3. Nine findings. Two of them are reachable by anyone who
can send an HTTP request, and both were reproduced rather than reasoned about —
the transcripts are in the findings themselves.

Each finding is tagged **[S3]** if it belongs in Sprint 3 and **[HW]** if it
belongs in Hardening week. The split is deliberate: Sprint 3 already carries two
workstreams and a mentor request, and a review that quietly becomes a third
workstream is a review that gets ignored. Only the items that are cheap, or that
the observability work will touch anyway, are marked S3.

**What this review did not do.** No penetration testing, no dependency review
beyond what Trivy already gates, no reading of the Gitea or Grafana
configuration surfaces beyond what this repository sets. It is a code and
configuration read plus two reproductions.

---

## Summary

| # | Finding | Severity | Where |
|---|---|---|---|
| F1 | `/echo` returns 500 on deeply nested JSON — unhandled `RecursionError` | High | **S3** |
| F2 | Request bodies are unbounded; `/echo` reflects them | High | **S3** |
| F3 | "The artifact is immutable" is a convention, not a mechanism | Medium | **HW** |
| F4 | Every published port binds `0.0.0.0`, including an unauthenticated registry | Medium | **S3** |
| F5 | `platform/.env` is inside the Docker build context | Medium | **S3** |
| F6 | No secret scanning anywhere in the pipeline | Medium | **HW** |
| F7 | The deployed container gets no runtime hardening | Low | **HW** |
| F8 | Everything is pinned, so nothing is ever patched between pushes | Low | **HW** |
| F9 | `docker image prune --force` is host-wide | Low | **S3** |

<<<<<<< Updated upstream
### Status

Updated as findings close, so this table and the repository do not drift apart.
A finding is only marked closed once the change is merged — the standard §6 sets
for everything else applies to this document too.

| # | Status |
|---|---|
| F1, F2 | Fixed, in review. Two corrections recorded against F1 below |
| F4, F5, F9 | Fixed, in review |
| F6 | Fixed, in review. Trivy `fs --scanners secret` after Ruff in `ci.yml`, plus the pinned `gitleaks` pre-commit hook. The `misconfig` scanner this section also recommends is *not* included and stays open in `PLAN.md` — the finding was secret scanning, and IaC triage is a separate piece of work |
| F3, F7, F8 | Open, Hardening week |

=======
>>>>>>> Stashed changes
---

## F1 — `/echo` returns 500 on deeply nested JSON [S3]

`request.get_json()` delegates to `json.loads`, which recurses once per level of
nesting. Past the interpreter's recursion limit it raises `RecursionError`, and
`RecursionError` is not a `ValueError`, so Flask never converts it into the
`BadRequest` that `app/app.py` catches. It propagates to the generic 500 handler.

Reproduced against the application as committed:

```
$ python3 -c "..."          # body: '[' * 100000 + ']' * 100000
nested-JSON status: 500
```

with the corresponding log line:

```json
{"level": "ERROR", "message": "Exception on /echo [POST]",
 "error_type": "RecursionError",
 "error_message": "maximum recursion depth exceeded while decoding a JSON array"}
```

The payload is 200 KB of brackets. It needs no authentication, no knowledge of
the application, and it is the same endpoint the incident demo already floods.

**Why this one leads.** The comment above the `except` in `app/app.py` argues
carefully about not logging attacker-controlled payloads, which is correct and
well reasoned — and it is guarding a handler that this request walks straight
past. The reasoning was sound; the exception set was too narrow. That is worth
saying plainly, because the fix is trivial and the lesson is not.

There is a second cost. `_finish_request` classifies anything ≥ 500 as `error`,
so a bored scanner can drive the error rate on the golden-signals dashboard from
outside, and the one alert rule Sprint 3 is building fires on someone else's
schedule.

<<<<<<< Updated upstream
**Fix.** Catch `RecursionError` in its own clause with its own reason —
grouping it with the two Werkzeug exceptions would hide that it arrives from a
different direction. The regression test is the deliverable: this is exactly the
kind of claim §6 says must be demonstrable.

### Correction, same day

Two things in the paragraphs above were wrong, and both were found by running
the fix on the interpreter the image actually uses rather than the one the
review was written on. Recorded here as a correction rather than edited away,
because the way they were wrong is the more useful part.

**The recursion depth is not a constant.** The reproduction above was done on
CPython 3.10, where C-level recursion is bounded by `sys.getrecursionlimit()`
and a thousand levels is the answer everywhere. CPython 3.12 replaced that with
a check against the real C stack, so the depth at which a parser gives way now
moves with the platform, the interpreter build and how much stack the thread
was given — and gunicorn serves this on worker threads, not the main one.
Measured on 3.12.13 on macOS: 8,000 levels parses, 16,000 raises. A first
attempt at a regression test asserted 400 at 5,000 levels and failed on 3.12
with a 200, which is the test being wrong rather than the application.

The consequence is that **nothing in this repository asserts that a particular
depth fails.** The tests and `smoke.yml` assert the contract — no body inside
the size limit produces a 5xx — and leave the depth at which the interpreter
agrees to the interpreter. A test pinned to a depth would go green for the wrong
reason the first time a runner had more stack, which is the failure mode §6
cares about most.

**The response path recurses too, and the first fix did not cover it.** `/echo`
reflects its input, so a deep document is walked twice: once by `json.loads` on
the way in and once by `jsonify` on the way out. The decoder and the encoder do
not give way at the same depth, so a body can parse successfully and then raise
`RecursionError` during serialisation — after the `try` block that was guarding
only the parse, and therefore straight into the 500 this finding is about.
Guarding the parse alone would have left the finding open against very nearly
the payload it was written for. The parse and the response are now inside one
`try`.

Neither correction changes the severity or the conclusion. F1 is real, it is
reachable inside the 64 KiB limit on 3.12 — 16,000 levels is 32,000 bytes,
half the ceiling — and F2 does not subsume it.
=======
**Fix.** Widen the catch and add the case to the suite:

```python
except (BadRequest, UnsupportedMediaType, RecursionError):
```

`RecursionError` is not in the same family as the other two and grouping it in
one tuple hides that; a separate `except` with its own one-line reason is the
honest version. Either way the regression test is the deliverable — this is
exactly the kind of claim §6 says must be demonstrable, and a test in
`tests/test_app.py` is what makes it so.

**Verified on Python 3.10; the image runs 3.12.** The default recursion limit is
1000 on both and the failure mode does not change, but the number of brackets
needed differs slightly. Re-run it inside the container before quoting a payload
size at a review.
>>>>>>> Stashed changes

---

## F2 — Request bodies are unbounded, and `/echo` reflects them [S3]

`MAX_CONTENT_LENGTH` is `None`, which is Flask's default and means no limit at
all. Reproduced:

```
MAX_CONTENT_LENGTH default: None
5MB body status: 200   echoed back bytes: 5242902
```

The container is capped at 256 MB by `deploy_app_memory`, and a request costs
roughly three copies of itself — the buffered body, the parsed structure, and
the serialised response. Two workers with four threads each is eight requests in
flight. The arithmetic is not close.

The memory limit means this is a crash and a restart rather than a host outage,
which is the compose-level defence working as designed. It is still a request
anyone can send that takes the application down, and the restart wipes the
`PROMETHEUS_MULTIPROC_DIR` on the way back up, so the metrics the incident would
be diagnosed from are the first casualty.

**Gunicorn is not the gap.** `limit_request_line` (4094) and
`limit_request_fields` (100) are already at sane defaults and bound the headers.
Only the body is unbounded, and only Flask can bound it.

**Fix.** One config line and a 413 handler:

```python
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
```

64 KB is well above anything the smoke test or `loadgen.sh` sends and well below
anything that hurts. Werkzeug returns 413 automatically once the limit is set;
adding an explicit handler is what stops that 413 arriving as an HTML error page
in a JSON API. Worth a line in `smoke.yml` too — a deploy that loses the limit
should fail, on the same argument that put the 400-on-wrong-content-type check
there.

---

## F3 — "The artifact is immutable" is a convention, not a mechanism [HW]

Non-negotiable #5 says the artifact is immutable and built once, and the whole
project rests on it. Nothing enforces it.

The registry is `registry:2` with no authentication, no TLS and no configuration
beyond a volume. Distribution allows a tag to be overwritten by default, so
`projecta-flask:<sha>` is a mutable pointer that this project treats as a
content address. CD then deploys by that tag. `pull: not_present` means a
redeploy would not even notice a substitution; a cold rollback — the one
scenario the RUNBOOK exists for — would pull whatever the tag points at now.

This needs write access to the registry to exploit, which today means F4. But
the claim in `CLAUDE.md` is unbacked with or without an attacker, and by §6 an
unproven claim is the finding.

**Fix — and this is the highest-value change in the review.** Deploy by digest
instead of by tag. `docker push` already prints the digest; capture it and hand
it to Ansible:

```yaml
- name: Push Docker image
  id: push
  run: |
    docker push localhost:5001/projecta-flask:${{ github.sha }}
    digest=$(docker image inspect --format '{{index .RepoDigests 0}}' \
      localhost:5001/projecta-flask:${{ github.sha }})
    echo "digest=${digest#*@}" >> "$GITHUB_OUTPUT"
```

and in the role, resolve `app_image_repository@{{ app_digest }}` when
`app_digest` is supplied, falling back to the tag when it is not so a hand-run
rollback still works from a SHA a human can type.

That turns "CD deploys what CI tested" from a sentence in a document into
something a reviewer can check by eye. The honest tradeoff: a digest is
unreadable and un-typeable, which is precisely why the tag path has to stay for
the human case, and that fallback is the remaining soft spot. Signing with
cosign would close it properly and is a Hardening-week-sized piece of work, not
an afternoon — name it as the production answer rather than building it.

---

## F4 — Everything publishes on `0.0.0.0` [S3]

Every port mapping in `platform/compose.yaml` uses the short form, which binds
all interfaces. So does `published_ports` in the deploy role. On any network the
laptop joins — campus wifi, a client's office, the TCS network — the following
are reachable by anyone on it:

| Port | Service | Authentication |
|---|---|---|
| 3000 / 2222 | Gitea, and its SSH | Yes |
| 5001 | Registry | **None. Push and pull.** |
| 9090 | Prometheus, with `--web.enable-lifecycle` | **None** |
| 3100 | Loki, `auth_enabled: false` | **None** |
| 3001 | Grafana | Yes |
| 8000 | The application, including `/metrics` | **None** |

The registry line is the one that matters, because it is the write access F3
needs. Prometheus is milder than it looks — the admin API is correctly left off,
so an anonymous caller gets `POST /-/reload` against a read-only mounted config
and little else — but it is still an unauthenticated control endpoint.

This also collides with risk B1/B2. If the answer to the mentor's open question
is "the TCS laptop", this stops being a laptop-privacy issue and becomes
something a corporate network scan finds.

**Fix.** Prefix every mapping with `127.0.0.1:`, in compose and in
`defaults/main.yml`. It costs one string per service and nothing else:

```yaml
ports:
  - "127.0.0.1:${REGISTRY_HTTP_PORT}:5000"
```

**The obvious objection, answered.** It does not break CD. Everything in the
pipeline reaches everything else by container name on `projecta-platform`, which
is why `deploy_app_smoke_vantage` exists — container-to-container traffic never
touches a published port. The `host` vantage a human uses from the laptop goes
over loopback and still works. The only thing lost is reaching the stack from a
phone or a second machine, which nothing in the project does.

---

## F5 — `platform/.env` is inside the Docker build context [S3]

`.dockerignore` contains `.env` and `.env.*`. Docker matches those patterns
against paths relative to the context root, so they exclude a root-level `.env`
and nothing else. `platform/.env` — the file holding the runner registration
token and the Grafana password — is sent to the daemon on every build.

It does not reach the image. The Dockerfile copies `app/` and
`gunicorn.conf.py`, so nothing pulls it in. This is a finding about the blast
radius of a future one-line change: the day someone writes `COPY . .`, or the
daemon stops being local, or a BuildKit cache is shared, the secret is already
in the room.

**Fix.** `**/.env` in `.dockerignore`. While there: `ansible/`, `platform/` and
`scripts/` are not excluded either, which is context sent over the socket on
every build for no reason.

**Not reproduced** — no Docker daemon was available during this review. Verify
in one command before writing it down as fixed:

```bash
docker build --no-cache -f - . <<'EOF'
FROM busybox
COPY . /ctx
RUN ls -la /ctx/platform/ || echo "platform/ correctly excluded"
EOF
```

---

## F6 — No secret scanning anywhere in the pipeline [HW]

`PLAN.md` already tracks pre-commit `gitleaks` as the one outstanding item whose
failure mode is hard to undo, and that assessment is right. The gap this review
adds is that a pre-commit hook is client-side and `--no-verify` skips it. A hook
is a convenience for the author; it is not a gate, and §4 of the non-negotiables
says a check that cannot fail the build is a log line.

History is clean today — 47 commits scanned for credential-shaped strings,
nothing found, and `platform/.env` has never been tracked. That is the good
news and it is also the whole argument: this is cheap to protect while it is
still true.

**Fix.** Trivy is already in the pipeline, already pinned at 0.72.0, and already
scans secrets on the image. Point it at the repository as well:

```yaml
- name: Scan the repository for secrets and misconfiguration
  timeout-minutes: 5
  run: |
    docker run --rm -v "$PWD:/src" aquasec/trivy:0.72.0 fs \
      --exit-code 1 --scanners secret,misconfig /src
```

Five lines converts an open P1 into a closed one and adds IaC misconfiguration
checks over the compose file and the Dockerfile for free. Keep the pre-commit
hook as well — it fails in two seconds instead of two minutes — but the CI step
is the gate. Expect the first run to be red on the compose file; that is
`--scanners misconfig` doing its job, and triaging it is the work.

---

## F7 — The deployed container gets no runtime hardening [HW]

The image runs as `appuser` (uid 10001), which is the important half and it is
already done. The container it runs in gets nothing else: no
`no-new-privileges`, no dropped capabilities, no read-only root filesystem.

None of this is exploitable on its own — it is defence in depth against a bug
that does not exist yet. It is on the list because it is four lines in
`roles/deploy_app/tasks/main.yml`, it is verifiable by the smoke test that
already runs, and it is the kind of thing a mentor asks about precisely because
it is cheap.

```yaml
security_opts:
  - no-new-privileges:true
cap_drop:
  - ALL
read_only: true
tmpfs:
  - /tmp
```

**`read_only: true` will break the deploy if the `tmpfs` line is forgotten.**
`PROMETHEUS_MULTIPROC_DIR` is `/tmp/prometheus-multiproc`, and gunicorn's
`on_starting` hook rebuilds that directory before the first worker boots. On a
read-only root it cannot, and the failure arrives as a container that never
reports healthy — which the deploy role handles correctly, but it will look like
a mystery for the ten minutes before someone reads the logs. Land the first two
lines and `read_only` separately.

---

## F8 — Everything is pinned, so nothing is ever patched between pushes [HW]

Non-negotiables #6 and #7 make the build reproducible. They also make it frozen:
the base image is a digest, every tool is an exact tag, every dependency is
hash-locked. Nothing in this repository ever updates itself, which is the
intended design and has a consequence worth stating.

Trivy fails the build on new HIGH/CRITICAL findings — but only when someone
pushes. A CVE published on a Tuesday against a `release/sprint3` that nobody
touches for a week is invisible for that week, and the pipeline stays green
throughout. "Scans block on HIGH/CRITICAL" in §6 is true and it is narrower than
it reads.

**Fix.** A scheduled workflow that re-runs the existing scan against the image
currently on `main`. It changes no gate and adds no dependency — it moves the
existing gate onto a clock.

**⬜ Unproven, and it should stay marked that way until it fires.** Whether
`schedule:` triggers work on act_runner v0.2.12 was not covered by the Sprint 3
spike. `ADR-0005` established that expression support was better than assumed;
cron support is a different subsystem and assuming it carries over is exactly
the mistake that ADR corrects. Add it to the spike, and if it does not work, a
documented limitation closes the item on the same terms the mentor already
accepted.

---

## F9 — `docker image prune --force` is host-wide [S3]

The cleanup step removes every dangling image on the machine, not just the ones
this build produced. On the current single-owner laptop that is fine and the
disk-pressure reasoning above the step is sound. If the answer to open question
1 is "the TCS laptop", it is deleting someone else's build cache.

`docker rmi` on the SHA tag immediately above already reclaims what this run
created. Either drop the prune, or scope it — `--filter label=app=projecta-flask`
— and say in the comment which host assumption it depends on.

---

## What is already right

Listing this is not politeness; a review that reports only findings gives a
false picture of the repository and is less useful at a defence, where the
question is as likely to be "what did you consider" as "what did you miss".

- **Metric cardinality is bounded at the source.** The route template rather
  than `request.path`, the `<unmatched>` bucket, and `--store_container_labels=false`
  on cAdvisor. The third one is the tell — the same rule applied to something
  the project does not own.
- **The inbound `X-Request-ID` is validated against a regex and replaced rather
  than rejected**, and there is a test named for the hostile case. Header
  reflection is the ordinary way log-injection and response-splitting arrive,
  and it is closed.
- **Log payloads are structured JSON**, so a hostile path or user-agent is
  escaped rather than able to forge a log line. `/echo` deliberately does not
  log its payload, and the comment explains why in terms of the log volume it
  would create.
- **The build context is minimal, the image is multi-stage**, dependencies are
  hash-verified at install time inside the builder, and the runtime stage
  carries no pip cache and no toolchain.
- **The ref gate passes `github.ref` through the environment** instead of
  interpolating it into the shell, with the reasoning written down. That is a
  real injection closed before it existed.
- **Git history is clean.** 47 commits, no credential-shaped strings,
  `platform/.env` never tracked.
- **Ansible asserts its input.** `app_version` is regex-checked as hex before it
  reaches a shell or an image reference, and there is no default.

---

## Suggested order

Sprint 3, in the sprint it is already in:

1. **F1 and F2** — together, one commit, with tests. They are the same endpoint
   and the same class of mistake, and the fix is under twenty lines. F1
   additionally protects the alert rule workstream A is building.
2. **F4 and F5** — configuration only, no behaviour change, ten minutes.
3. **F9** — one line, while the file is open.

Hardening week:

4. **F3**, digest-pinned deploys. The largest piece of work here and the one
   that most improves what the project claims about itself.
5. **F6**, Trivy `fs` in CI, plus the gitleaks hook already planned.
6. **F7**, container runtime flags, `read_only` landed separately.
7. **F8**, once the act_runner cron question has an answer either way.

F3 is the one to talk about at the next review even if it is not built.
"Immutable by convention, and here is the mechanism that would enforce it" is a
better answer than either a silent gap or a rushed implementation.
