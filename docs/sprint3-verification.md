# Sprint 3 — verification checklist

**Closed 2026-08-11.** Sections 0 through 8 all carry results and dates, and the
status tables elsewhere moved only after that. Two things came out of the
closing pass and are recorded rather than smoothed over: the error-rate panel
was colouring from the palette instead of its thresholds, and the rollback
drill's third run drifted from 34s to 37s.

This file was written when everything in the observability branch was **written
and unproven**, as the list of things that had to be run before any of it could
be marked ✅ anywhere else, and the place the results get recorded. It is kept
in that form on purpose — a checklist rewritten after the fact to look like it
always passed is not evidence of anything.

The standard is [`PLAN.md`](PLAN.md) §6: a claim that cannot be demonstrated is
marked ⬜, and a status changes only when it has been run and the result written
down with a date. Do not tick a box because the code looks right.

Work top to bottom — later steps depend on earlier ones. Each step says what
"passed" looks like, so a partial result is recognisable as one.

**Record results in the Result column.** Date them. If something fails, write
what happened rather than deleting the row — a failure that was fixed is
evidence the check works.

---

## 0 — Before anything else: recompile the locks

`requirements.txt` and `requirements-dev.txt` on this branch were generated with
`uv pip compile --python-version 3.12`, not with the `pip-compile` command
[`DEVELOPMENT.md`](DEVELOPMENT.md) documents. The resolution is correct for
Python 3.12 and the content should match, but the header records the wrong tool
and the repository has one documented way to produce a lock.

This is the first step because a lock nobody can reproduce with the documented
command is the same class of problem as the gunicorn drift closed in #28.

```bash
pip-compile --allow-unsafe --generate-hashes --strip-extras requirements.in
pip-compile --allow-unsafe --generate-hashes --strip-extras requirements-dev.in
git diff --stat requirements.txt requirements-dev.txt
```

| Check | Passed when | Result |
|---|---|:--:|
| 0.1 Both locks recompile on Python 3.12 | The commands exit 0 | ✅ |
| 0.2 Package set is unchanged | Only the header lines differ, plus version churn if PyPI moved | ✅ |
| 0.3 `gunicorn==23.0.0` is in **both** locks | `grep -c '^gunicorn==23.0.0' requirements.txt requirements-dev.txt` → `1` and `1` | ✅ |
| 0.4 Result committed | `git commit --amend` or a follow-up commit on the same branch | ✅ |

If the package set differs by more than a version bump, stop and read the diff
before continuing — that is a real finding, not a formality.

---

## 1 — The application, locally

No Docker needed. This is the fastest signal and it gates everything else.

```bash
pytest && ruff check .
pytest --cov=app --cov-fail-under=80
```

| Check | Passed when | Result |
|---|---|:--:|
| 1.1 Suite green | 25 passed | ✅ |
| 1.2 Coverage above the gate | Reported 100% on `app/` | ✅ |
| 1.3 Ruff clean | `All checks passed!` | ✅ |

Then look at the log output with your own eyes, because a test asserting a field
exists is not the same as a human confirming the line is readable:

```bash
python -c "
from app.app import app
c = app.test_client()
c.get('/', headers={'X-Request-ID': 'demo-1'})
c.post('/echo', data='{\"bad\"', content_type='application/json')
"
```

| Check | Passed when | Result |
|---|---|:--:|
| 1.4 Each line is one JSON object | Parses with `jq .` if piped through it | ✅ |
| 1.5 The supplied id is honoured | First line has `"request_id": "demo-1"` | ✅ |
| 1.6 The bad request is WARNING | Second pair of lines has `"level": "WARNING"`, `"status": 400` | ✅ |

**Run 2026-08-06**, Python 3.12.13 on macOS/arm64, pytest 9.1.1. 25 passed
(24 at first run; the twenty-fifth was added by the section 2 findings below),
ruff clean, `app/` at 100%. Both locks recompiled with the documented
`pip-compile` command and produced **no content change** against the `uv`-built
versions they replaced — the resolution was already correct for 3.12, and only
the recorded command differed. `gunicorn==23.0.0` present in both, so the drift
closed in #28 has not reopened.

The two `/echo` lines share a `request_id`, which is the property the whole
metric-to-log pivot rests on: the line that says *what went wrong* and the line
that says *how the request ended* are joinable without a timestamp guess.

---

## 2 — The image

**Published on 8001, not 8000.** The deployed `projecta-flask` container already
holds 8000 on this host — `docker run -p 8000:8000` fails with "port is already
allocated". Stopping the deployed app to free the port would be the wrong
instinct: this check is about whether a freshly built image behaves, and it
should not require taking the running one down. Found 2026-08-06, on the first
run of this section.

```bash
docker build -t flaskapp:dev .
docker rm -f obs-check 2>/dev/null
docker run --rm -d --name obs-check -p 8001:8000 flaskapp:dev
sleep 8
docker inspect -f '{{.State.Health.Status}}' obs-check
curl -s -D- -o /dev/null localhost:8001/ | grep -i x-request-id
curl -s localhost:8001/metrics | head -20
docker logs obs-check | tail -5
```

| Check | Passed when | Result |
|---|---|:--:|
| 2.1 Image builds | Build exits 0 | ✅ 2026-08-06 |
| 2.2 hadolint still clean | `docker run --rm -i hadolint/hadolint:v2.14.0 /bin/hadolint --failure-threshold info - < Dockerfile` exits 0 | ✅ |
| 2.3 `/metrics` serves exposition format | `http_requests_total` appears with `# HELP` and `# TYPE` | ✅ |
| 2.4 Response carries the request id | `X-Request-ID` header present and non-empty | ✅ |
| 2.5 Container logs are JSON, gunicorn's included | No plain-text `[INFO] Starting gunicorn` line — it should be a JSON object | ✅ |
| 2.6 The healthcheck still passes | `docker inspect -f '{{.State.Health.Status}}' obs-check` → `healthy` | ✅ |
| 2.8 Exactly one log record per request | No `"logger": "gunicorn.access"` lines — only `app.app` with `"event": "http_request"` | ✅ |

**2.7 — multiprocess metrics, the one most likely to be wrong.** Two gunicorn
workers write to a shared directory; if that is misconfigured the counters
appear to jump around between scrapes. Hit the app twenty times and check the
total is twenty, not roughly ten:

```bash
for i in $(seq 1 20); do curl -s -o /dev/null localhost:8001/; done
curl -s localhost:8001/metrics | grep 'http_requests_total{.*endpoint="/"'
docker exec obs-check ls /tmp/prometheus-multiproc
```

| Check | Passed when | Result |
|---|---|:--:|
| 2.7 Counter totals across workers | The value is `20`, and the directory lists two or more `.db` files | ✅ |

**Run 2026-08-06.** Healthy in under 8s. `/metrics` served the exposition
format. 2.7 returned `21.0` against twenty requests — the extra one is the
header check above it, and a number that is *explainably* off by one is better
evidence than a round one, because it means the counter tracks reality rather
than the loop. `/tmp/prometheus-multiproc` held `counter_7.db`, `counter_8.db`,
`histogram_7.db`, `histogram_8.db`: both workers writing, one aggregated answer.
The failure this check exists to catch — a scrape returning roughly half the
traffic — is ruled out.

**2.5 failed, and the fix is worth recording.** The arbiter's six start-up lines
were plain text while every request line was JSON:

```
[2026-08-06 07:27:22 +0000] [1] [INFO] Starting gunicorn 23.0.0
{"timestamp": "...", "level": "INFO", "logger": "app.app", "message": "request", ...}
```

`configure_logging()` is called when `app.app` is imported, which happens in
each worker — long after the arbiter has logged through a logger that call will
never reach. The docstring in `app/logging_config.py` claimed gunicorn's loggers
were re-pointed; that was true for the workers and false for the process doing
the talking at start-up.

Fixed with `logconfig_dict` in `gunicorn.conf.py`, which gunicorn hands to
`dictConfig()` inside `Logger.setup()` before the first line is written. Both
mechanisms stay: one covers gunicorn, the other covers `pytest` and `flask run`.

**And the fix broke something else, which is the better story.** The rebuild
came back all-JSON, 2.5 green — with a `gunicorn.access` line at the top that
had not been there before. `accesslog = None` had switched the access log off;
defining `logconfig_dict` switched it back on, because `Logger.access()` starts:

```python
if not (self.cfg.accesslog or self.cfg.logconfig
        or self.cfg.logconfig_dict or ...):
    return
```

So the fix for the plain-text start-up lines silently restored the duplicate
access record those lines were fixed alongside — two log entries per request,
and every rate derived from logs wrong by a factor of two. Exactly the failure
mode the original `accesslog = None` comment was written to prevent, reintroduced
by the commit that quoted it. Closed with a `NullHandler` on `gunicorn.access`
and check 2.8 added, because a property worth stating in a comment is a property
worth failing a build over.

**Third attempt, and the point where the pattern became the finding.** The
NullHandler did not survive either: `configure_logging()` runs in each worker on
`app.app` import and did `gunicorn.access.handlers = [console]`, putting back the
handler `gunicorn.conf.py` had just removed. Duplicate access line, again.

Three fixes, each individually correct, each defeated by the other configuration
path — because two files owned the same loggers and the winner depended on
process lifecycle rather than on anything readable in either file. Patching a
fourth time would have been the wrong move. Ownership is now disjoint:
`gunicorn.conf.py` owns every `gunicorn.*` logger, `configure_logging()` owns the
root logger, neither reaches into the other. `test_configure_logging_does_not_touch_gunicorn_loggers`
fails if that boundary is crossed again.

Known consequence, stated rather than guarded: `gunicorn app.app:app` without
`--config gunicorn.conf.py` produces plain-text gunicorn lines. The Dockerfile
always passes it.

Three findings in one section, all the same class: a setting that means what it
says until another setting is present. None was findable by reading the code —
only by running it and reading the output line by line. That is the argument for
this checklist existing, and it is worth making at review with these three as
the evidence.

**Section 2 closed 2026-08-06.** All eight checks green after the third fix:
`grep -c gunicorn.access` on the container's log returns 0, start-up lines are
`gunicorn.error` JSON, request lines are `app.app` JSON, one per request.

Worth carrying to the review. Nothing was broken — Alloy passes an unparsed line
through with its container label intact, so the logs would have reached Loki
either way. It would have shown up as a handful of entries per container start
with no `level` label, which is exactly the kind of thing you notice six months
later while looking for something else. A checklist item written to fail on a
literal string is what caught it.

```bash
docker stop obs-check
```

---

## 3 — The stack comes up

```bash
cd platform
# The six new variables must exist in .env — copy them from .env.example.
grep -E 'PROMETHEUS|LOKI|ALLOY|GRAFANA|CADVISOR|NODE_EXPORTER' .env
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
```

| Check | Passed when | Result |
|---|---|:--:|
| 3.1 Every pinned image pulls | No `manifest unknown` — if one fails, the tag in `.env.example` is wrong and needs correcting there, not just locally | ✅ |
| 3.2 All nine services are Up | `ps` shows gitea, registry, act-runner, prometheus, cadvisor, node-exporter, loki, alloy, grafana | ✅ |
| 3.3 Nothing is restart-looping | Wait 2 minutes, run `ps` again, `RESTARTS` has not climbed | ✅ |
| 3.4 Grafana is on 3001, not fighting Gitea | `curl -s localhost:3001/api/health` → `"database": "ok"` | ✅ |
| 3.5 Memory limits hold | `docker stats --no-stream` — nothing sitting at 100% of its limit | ✅ |
| 3.6 Host budget survived | Total across projecta containers under ~4 GB (PLAN.md §5) — **record the actual number**, it replaces an estimate | ✅ |

**Run 2026-08-06.** All six images pulled on the pinned tags — no `manifest
unknown`, so the versions in `.env.example` are real. All nine services Up after
the node-exporter fix below.

**3.6 — the estimate, replaced by a number.**

| | Idle memory |
|---|---|
| Observability only (prometheus, cadvisor, node-exporter, loki, alloy, grafana) | **350 MiB** |
| Whole stack including gitea, registry, act-runner, projecta-flask | **769 MiB** |

`PLAN.md` §5 budgets 3–4 GB. The measured figure is **under a quarter of the
low end** — the estimate was pessimistic by roughly a factor of five, and the
"drop node_exporter first if constrained" contingency has not been needed.
Idle, though: nothing was being scraped hard and no logs were flowing. Re-measure
during section 7, when the load generator is running, and record both.

**Alloy has the least headroom** at 73 MiB against a 256 MiB limit — 29% while
doing nothing. It is the component whose cost scales with log volume, so it is
the first of the six to watch under the burst. Nothing else is above 20% of its
limit.

**3.1 failed on the first attempt, and took two services down with it.**
node-exporter's upstream-recommended `/:/host:ro,rslave` is refused by Docker
Desktop:

```
Error response from daemon: path / is mounted on / but it is not a shared or
slave mount
```

The VM's root has no mount propagation set. Worse than a failed container:
compose aborts the entire `up` on the error, so Grafana and Alloy were left in
`Created` and never started — one unsupported mount option looked like three
broken services. Fixed by dropping `rslave`, which only buys visibility of
filesystems mounted after start-up, and nothing here mounts anything at runtime.

**What that surfaced is worth more than the fix.** On macOS, node_exporter
measures the Docker Desktop VM, not the MacBook. "Host memory available" is the
VM's 7.75 GiB allocation, and CPU pressure from anything outside Docker is
invisible. The panel still answers "how much of the pool is left", which is the
actionable question, but it cannot answer "is the laptop struggling" — and a
reviewer comparing it against Activity Monitor would have found that out in the
worst possible setting. Now stated on the service, on the dashboard and on both
panels that would otherwise be quoted.

---

## 4 — Prometheus is scraping

**The running container has no `/metrics`.** `projecta-flask` is serving the
image from before this branch, so Prometheus will scrape it and get a 404 until
a new artefact is deployed. And a feature branch deliberately publishes nothing
— `ref_gate` sets `ships=false`, so pushing to Gitea proves the build without
putting an image in the registry.

So for this check the artefact is built and pushed by hand. This is the one
place in the project where that is the right thing to do, and it is worth being
explicit that it is a *verification* step and not how delivery works: CD deploys
what CI tested, and nothing here changes that.

```bash
SHA=$(git rev-parse HEAD)
docker build -t localhost:5001/projecta-flask:$SHA .
docker push localhost:5001/projecta-flask:$SHA
cd ansible
ansible-playbook playbooks/deploy.yml -e app_version=$SHA
```

Section 8 re-runs the same thing the supported way, through the pipeline, and
that is the run that counts for the delivery claim.

Then open `http://localhost:9090/targets`.

| Check | Passed when | Result |
|---|---|:--:|
| 4.1 All four targets UP | projecta-flask, cadvisor, node-exporter, prometheus | ✅ |
| 4.2 App metrics are present | Query `http_requests_total` returns series | ✅ |
| 4.3 Container metrics are present | Query `container_memory_working_set_bytes{name=~"projecta-.+"}` returns series | ✅ |
| 4.4 Host metrics are present | Query `node_memory_MemAvailable_bytes` returns a series | ✅ |

**4.5 — the cardinality claim, measured.** ADR-0007 argues the series count is
bounded by the shape of the app rather than its traffic. Prove it:

```bash
# before
curl -s 'localhost:9090/api/v1/query?query=count(http_requests_total)'
# (a matcher in a query needs -G --data-urlencode; hand-encoding =~ as %2B
#  produces "parse error: unexpected character after '='". Found 2026-08-06.)
scripts/loadgen.sh --baseline 30 --baseline-only
# after
curl -s 'localhost:9090/api/v1/query?query=count(http_requests_total)'
# and confirm no path ever became a label.
#
# match[] is not optional. Without it this endpoint returns every value of the
# label `endpoint` across every metric in the database, including Prometheus's
# own — its Consul service-discovery metrics carry endpoint="catalog" and
# endpoint="service", which have nothing to do with this application. The first
# run of this check reported "catalog" and looked like a cardinality breach.
# A gate that goes red because an unrelated component has a label of the same
# name is a gate people learn to skim past. Found 2026-08-06.
curl -s 'localhost:9090/api/v1/label/endpoint/values?match[]=http_requests_total'
```

| Check | Passed when | Result |
|---|---|:--:|
| 4.5 Series count barely moves under load | Before and after differ by a handful, not by the request count | ✅ |
| 4.6 `endpoint` values are route templates only | **Every** value is a route template or `<unmatched>`. Not a fixed list — an endpoint nothing has called yet is simply absent, which is correct. The property is that no value is a concrete URL | ✅ |

**4.3 cost the longest detour of the day, and the finding is a prerequisite.**
`container_memory_working_set_bytes{name=~"projecta-.+"}` returned nothing.
cAdvisor was scraping fine, the target was green, and every container metric
arrived as `id="/docker/<sha>"` with no `name` label — a failure that reports
itself nowhere.

Two causes, and only fixing both works:

1. `/var/run:/var/run:ro`, the upstream example, gives cAdvisor no Docker
   socket on Docker Desktop. The path `/var/run/docker.sock` is special-cased
   and bound to the VM's real socket; `/var/run` as a directory maps the *Mac's*
   `/var/run`, which has none. Alloy had been working all along by mounting the
   socket by name.
2. Docker Desktop's **containerd image store**, which is the default. cAdvisor
   then connects, lists containers, and fails on each with `failed to identify
   the read-write layer ID — open /rootfs/var/lib/docker/image/overlayfs/
   layerdb/mounts/<id>/mount-id: no such file or directory`. It expects the
   classic graph-driver layout, which containerd does not have.

Fixing (1) alone got as far as "Registration of the docker container factory
successfully" and no further, which is why both are recorded. After turning
containerd off: **zero** `Failed to create existing container` lines, all ten
containers named, `count(...{name=~"projecta-.+"})` = 10.

**This is a prerequisite for the clean-machine test**, not a footnote. A fresh
Docker Desktop defaults to containerd and reproduces the empty panels exactly.
Written up on the `cadvisor` service in `platform/compose.yaml` and in
`DEVELOPMENT.md` §8.

**Free evidence from the rebuild.** Switching the image store emptied the local
cache, and the deploy that followed asked for a SHA that was never pushed. The
Sprint 2 failure handling behaved correctly on a failure mode it was never
designed for — the *pull* failed, not the smoke test — and it did not invent a
rollback target:

```
Nothing was running before this deploy, so there is no previous SHA
to roll back to. Fix forward.
```

`rescued=1` in the recap: the block/rescue caught it, captured logs, and stopped
with a true statement. Until now that path had only been exercised with the
deliberately broken image in the rollback drill. Worth adding to
`docs/RUNBOOK.md` as a second, unplanned rehearsal.

**4.5 — the ADR-0007 claim, measured.** Before: **5** series. 125 requests
through `loadgen.sh --baseline 30 --baseline-only`. After: **6**.

One new series against a hundred and twenty-five requests, and the new one is
not a consequence of volume at all — it is `endpoint="/"`, a route nothing had
called on this container until the load generator did. Call it again a million
times and the count stays at six.

That is the whole of ADR-0007 in two numbers. Had the label been
`request.path`, the same run would have produced 5 + 125. The check is worth
re-running after any change to `app/metrics.py`, because this is the property
that fails silently: nothing breaks, memory just grows.

`node_memory_MemAvailable_bytes` reported 6.77 GB free of the VM's 7.75 GiB —
consistent with the 769 MiB measured in section 3, and a reminder that this is
the VM's memory rather than the Mac's.

**Run 2026-08-06.** All four targets UP within a minute of the deploy. The
deploy itself was clean — `ok=11 changed=1`, and the container's `version` label
moved from `b9d9f23…` to `242e044…`, so the artefact Prometheus is scraping is
the one just built.

**4.6 passed once the query was scoped.** The unscoped version returned
`catalog`, which is Prometheus's own Consul service-discovery label and belongs
to no part of this application — a false positive, and the fix is in the command
above. Scoped to `http_requests_total`:

```
["/echo","/health","/metrics","/ready"]
```

Four route templates, no concrete URLs, nothing invented. `/` and `<unmatched>`
are absent because nothing has requested them on this container yet, which is
the correct behaviour and the reason this check tests a property rather than a
list.

Ground truth from the app itself, worth keeping because it shows two labels
doing their job at once:

```
http_requests_total{endpoint="/health",method="GET",status="200"} 19.0
http_requests_total{endpoint="/metrics",method="GET",status="200"} 12.0
http_requests_total{endpoint="/echo",method="POST",status="200"} 1.0
http_requests_total{endpoint="/echo",method="POST",status="400"} 1.0
http_requests_total{endpoint="/ready",method="GET",status="200"} 1.0
```

`/echo` is two series, not one, split by `status` — the deploy's smoke test
exercises both the valid payload and the wrong Content-Type, and the
instrumentation tells them apart. Five series for a fully exercised application.
That number is the argument in ADR-0007, stated as a measurement.

---

## 5 — Logs reach Loki

```bash
curl -s 'localhost:3100/loki/api/v1/labels'
curl -s -G 'localhost:3100/loki/api/v1/query_range' \
  --data-urlencode 'query={container="projecta-flask"} | json' \
  --data-urlencode 'limit=5' | jq '.data.result | length'
```

| Check | Passed when | Result |
|---|---|:--:|
| 5.1 Loki has labels from Alloy | `container`, `service`, `level`, `platform` appear | ✅ |
| 5.2 App logs are queryable | The query returns entries | ✅ |
| 5.3 JSON parsing works | `\| json \| status=400` returns only the failed requests | ✅ |
| 5.4 Timestamps are the app's, not Alloy's | A line backdated three hours is stored at its claimed time, not at ingest time | ✅ |

**5.4 — and the check as originally written could not fail.** The wording was
"entry time matches the `timestamp` field in the line, within a second." Under
live traffic Alloy reads a line milliseconds after the application writes it, so
the app's clock and the ingest clock agree to well inside a second whether or
not `stage.timestamp` is doing anything at all. Deleting that entire block from
`config.alloy` would have left this check green. It was a log line, not a gate.
It is rewritten above to force the two timestamps apart.

A throwaway container emits two lines: one backdated three hours, and one at the
current time. The second is a control — without it, a probe Alloy never
collected is indistinguishable from a probe that passed. That is not
hypothetical: the first attempt used `--rm` and a 24-second lifetime, the
container was deleted before the ten-second discovery loop could attach to it,
and the query returned nothing. An empty result read exactly like a failure.
Hence the control, and hence `-d` with a long trailing sleep.

```bash
NOW=$(python3 -c "import datetime as d; print(d.datetime.now(d.timezone.utc).isoformat(timespec='milliseconds'))")
OLD=$(python3 -c "import datetime as d; print((d.datetime.now(d.timezone.utc)-d.timedelta(hours=3)).isoformat(timespec='milliseconds'))")

docker run -d --name probe54 alpine sh -c \
  "sleep 25; \
   echo '{\"timestamp\":\"$NOW\",\"level\":\"INFO\",\"logger\":\"probe\",\"message\":\"control\"}'; \
   echo '{\"timestamp\":\"$OLD\",\"level\":\"INFO\",\"logger\":\"probe\",\"message\":\"backdated\"}'; \
   sleep 600"
```

**Run 2026-08-07.**

```
backdated  claimed=06:40:44.525  stored=06:40:44.525  drift=0.000s
control    claimed=09:43:55.311  stored=09:43:55.311  drift=0.000s
```

The backdated line was written to stdout at 09:40:56 and Loki filed it at
06:40:44 — three hours and twelve seconds before it was collected. Alloy is
using the application's clock, not its own. Had `stage.timestamp` been missing
or silently failing, that line would have landed at 09:40:56 with everything
else, and the derived-field link from the error rate panel would drop a reviewer
three hours away from the incident they clicked on.

**5.5 — the second cardinality claim (ADR-0007, rule 2).** `request_id` must not
have become a Loki stream label:

```bash
curl -s 'localhost:3100/loki/api/v1/labels' | jq '.data'
curl -s 'localhost:3100/loki/api/v1/label/level/values' | jq '.data'
```

| Check | Passed when | Result |
|---|---|:--:|
| 5.5 `request_id` is **not** in the label list | It appears only inside the line body | ✅ |
| 5.6 `level` has a handful of values | INFO, WARNING, ERROR, DEBUG — not hundreds | ✅ |
| 5.7 A line far enough behind the stream head is dropped, not filed late | `loki_discarded_samples_total{reason="too_far_behind"}` counts it | ✅ |

**Run 2026-08-06.** Stream labels: `container`, `level`, `platform`, `service`,
`service_name`. **`request_id` is not among them**, which is rule 2 of ADR-0007
holding in the half of the stack where it is easiest to get wrong. `level` has
two values so far, INFO and WARNING, because nothing has produced an ERROR yet.

**A screenshot of this will look alarming, and it is fine.** The query result's
`stream` object lists `request_id`, `endpoint`, `duration_ms`, `path` and the
rest — because `| json` unpacks them *at query time*. They are not indexed and
they create no streams. A reviewer looking at that output is entitled to ask
whether the cardinality rule was really followed; the answer is the `/labels`
endpoint above, and it is worth having that comparison ready rather than
improvised.

Two labels arrived that this project did not configure: `service_name`, which
Loki 3.x derives automatically, and `detected_level` alongside our own `level`
in the query result. Harmless, and worth knowing they are Loki's doing rather
than a mistake in `config.alloy`.

**5.7 — `stage.timestamp` preserves correlation; it does not recover a long
backlog.** The two 5.4 probe lines went to the same stream in the same push. The
control, at the current time, was accepted and moved the stream head to
09:43:55. The backdated line, three hours behind that head, was not:

```bash
curl -s localhost:3100/metrics | grep loki_discarded_samples_total
loki_discarded_samples_total{reason="too_far_behind",tenant="fake"} 1
```

Exactly one sample, exactly that line. The earlier probe's backdated line
survived only because its stream was empty at the time and there was no head to
be behind. Loki accepts out-of-order writes within roughly half of
`max_chunk_age`; three hours is outside that window.

The consequence, stated rather than buried: `stage.timestamp` keeps the
metric-to-log correlation honest for a backlog Alloy catches up on within about
an hour, and beyond that Loki discards the entries instead of filing them late.
A container down for a morning does not get its logs back. The
`reject_old_samples_max_age: 24h` in `loki-config.yaml` is *not* the binding
limit — the out-of-order window is, and it is far tighter than that setting
suggests.

**The ring errors in Loki's own log are the laptop, not Loki.** `docker logs
projecta-loki` carries a pattern that looks alarming:

```
level=error caller=scheduler.go:635 msg="failed to query the ring ..."
  err="at least 1 healthy replica required, could only find 0
       - unhealthy instances: 127.0.0.1:9096"
level=warn caller=basic_lifecycler_delegates.go:147
  msg="auto-forgetting instance from the ring because it is unhealthy
       for a long time" instance=c4acccfaff47 last_heartbeat="06:23:12"
```

Loki has not restarted — `OOMKilled=false`, `restarts=0`, up since 2026-08-06
08:55 — so this is not a crash loop, and `last_heartbeat` advances between
occurrences rather than freezing, which a dead process would not do.

The stack diagnosed itself. Every Prometheus target gapped at the same two
instants, over the same durations:

```
prometheus/localhost:9090                  [('06:28:00', '660s'), ('06:43:30', '1440s')]
cadvisor/projecta-cadvisor:8080            [('06:28:00', '630s'), ('06:43:30', '1440s')]
projecta-flask/projecta-flask:8000         [('06:28:00', '660s'), ('06:43:30', '1440s')]
node-exporter/projecta-node-exporter:9100  [('06:28:00', '630s'), ('06:43:30', '1440s')]
```

Prometheus lost sight of *itself* at the moment it lost the other three, which
no single-service fault explains. `pmset -g log` puts the host in 'Maintenance
Sleep' from 08:23:14 to 08:38:20 local, and again from 08:38:22 until the lid
opened at 09:10:26 — 06:23–06:38 and 06:38–07:10 UTC. Loki's ring errors land on
the wakes: the process resumes, finds its own heartbeat fifteen minutes stale,
declares the ring unhealthy, and recovers a few seconds later.

Two things follow. The twenty-four minute hole in the metrics is real and
belongs in a screenshot honestly rather than cropped out. And the review needs
the machine awake — `caffeinate -dimsu` for the duration — because a
'Maintenance Sleep' during the incident walkthrough would empty every panel at
once, in front of the mentor, for a reason that has nothing to do with the
pipeline.

`noDataState: NoData` in `rules.yaml` is what stops this also producing a
spurious page on every sleep: the rule reports NoData rather than firing. That
was configured for a different reason and happens to cover this one.

---

## 6 — Grafana, provisioned

Open `http://localhost:3001`, log in with the credentials from `.env`.

| Check | Passed when | Result |
|---|---|:--:|
| 6.1 Both datasources exist and test green | Connections → Data sources → Save & test on each | ✅ |
| 6.2 Both dashboards are in the "Project A" folder | Not in "General" — if they are, the provider file did not load | ✅ |
| 6.3 No panel says "datasource not found" | The uids in the JSON match the provisioned uids | ✅ |
| 6.4 Golden-signals panels render data | Rate, error rate, latency, status all show lines after some traffic | ✅ |
| 6.5 Host dashboard renders data | "Scrape targets up" shows four green, CPU and memory draw | ✅ |
| 6.6 Dashboards are read-only | The panel edit option is absent — `allowUiUpdates: false` took effect | ✅ |
| 6.7 The alert rule is loaded | Alerting → Alert rules → "/echo is rejecting requests" exists, state Normal | ✅ |

**Run 2026-08-06.** Both dashboards in the "Project A" folder, every panel
bound to a provisioned datasource, the logs panel returning the two WARNING
lines from a malformed `/echo` — with a shared `request_id`, visible in the
screenshot. The alert rule shows in `Project A › projecta-app`, state Normal,
health ok, badged **Provisioned**, evaluating every 30s.

**6.6 confirmed through the API rather than by trying to break it.**
`/api/dashboards/uid/projecta-app` reports `"provisioned": true` and
`"editable": false`; the toolbar offers "Make editable" and no Save, and
`?editview=settings` does not open. `canSave: true` also appears in that
response and is not a contradiction — it is the *role* permission, while the
provisioning lock is enforced separately on write.

**6.4 exposed a defect in the error-rate panel: the Y axis ran to 10000%.**
An error *ratio* cannot exceed 1, so an axis a hundred times past that is a
query bug. The cause was mine, and the panel description said it out loud:

> clamp_min keeps the ratio defined when there is no traffic at all, rather
> than drawing a gap that looks like an outage.

That reasoning is backwards twice over. Dividing by a floor of `0.001` lets a
real numerator produce a ratio of 100. And the value it invents when there is
no traffic is **0%** — which renders green and reads as "we are watching, all
is well", when the truth is that there is nothing to watch. For an error-rate
panel that is the most dangerous possible failure: healthy-looking blindness.

Fixed in both places that had it, the panel and the alert rule. Without the
clamp, no traffic yields an empty vector — a gap on the graph, `NoData` on the
rule, which `noDataState: NoData` already handles. `max: 1` added to the panel
so the axis cannot silently rescale past 100% again.

Worth carrying to the review as the counterpart to the cardinality result: the
same instinct that says "don't leave a gap in the graph" is the one that
produces a dashboard which lies quietly.

---

## 7 — The incident, end to end

This is the demo. Run it exactly as it will be run for evidence.

```bash
scripts/loadgen.sh
```

| Check | Passed when | Result |
|---|---|:--:|
| 7.1 Baseline is visible | Error rate sits at 0 for the first minute — the "before" the demo needs | ✅ |
| 7.2 Error rate climbs past 10% | Panel goes orange then red | ✅ |
| 7.3 The rule goes **Pending** | Visible for about a minute — this is the `for: 1m` clause | ✅ |
| 7.4 The rule goes **Firing** | Alerting page shows Firing | ✅ |
| 7.5 The data link opens Loki | Clicking the error-rate panel's link lands in Explore with the query and the same time range | ✅ |
| 7.6 The filtered query returns the failures | Only `status >= 400` lines | ✅ |
| 7.7 `request_id` renders as a link | Expand a line — "All logs for this request" appears | ✅ |
| 7.8 Clicking it returns that request's lines | Both the `bad_request` line and the `http_request` line, same id | ✅ |
| 7.9 The whole path needs no shell | No SSH, no `docker logs`, no grep | ✅ |

**7.5 was the step most likely to fail, and it passed.** The Explore deep link
used Grafana 11's `panes` schema, written from documentation and never executed
before 2026-08-06 — the only part of this stack in that position. It opened
Explore on the Loki datasource with
`{container="projecta-flask"} | json | status >= 400` and, critically, **carried
the time range across**: 11:15:38–11:30:38, the dashboard's own fifteen-minute
window. 385 lines, with the logs-volume histogram showing the burst as a solid
block between 11:21 and 11:22.

Carrying the time range is what makes this a pivot rather than a bookmark. A
link that lands on "the last hour of everything" would still leave the reader
to find the moment by hand, which is the manual correlation step the sprint
exists to remove.

**The link now exists twice**, and the second one was added because of how this
check went. A field data link only appears after clicking a point on the line —
fine when driving the dashboard, useless in a still image, and the Sprint 3
evidence is stills. The same URL is now also a panel link in the header, where
it is visible without interacting. Found by trying to follow this instruction
and finding nothing happened on the panel title.

**Run 2026-08-06, after the error-rate fix.** The incident produced exactly the
shape the demo needs:

| | |
|---|---|
| Error rate before the burst | **0%**, flat, for the whole baseline minute |
| Error rate at peak | **96.5%** (mean 7.13% over the 15m window) |
| `/echo` request rate at peak | 4.27 req/s |
| Latency | p50 2.50 ms · p95 4.75 ms · p99 4.95 ms |
| Alert | Normal → Pending → **Firing**, `for 1m`, evaluating every 30s |

**96.5% and not 100%, which is the better number.** The baseline's 200s are
still inside the 1-minute rate window. A ratio that hit exactly 100% would mean
the measurement could only see the failures, and that would be worth
investigating rather than celebrating.

The alert detail page carries its own labels (`service=projecta-flask`,
`severity=warning`), the description that names `scripts/loadgen.sh` as the
cause, and a runbook link — so someone who has never seen this project can get
from the alert to the procedure without asking. All of it from the provisioned
file; the **Provisioned** badge is visible next to the rule name.

Screenshots deliberately not taken today. The evidence pack is produced the day
before the review, from this same script, so the stills are of a current run
rather than a stale one.

**7.7 and 7.8 took three attempts, and the third finding is the one to keep.**

The first version pointed the derived field at the Loki datasource with
`datasourceUid`. Grafana treats that as a datasource-to-datasource jump: it
hands the *field value* to the target and ignores `url` as a query. The link
fired, Explore split, and the new pane sat empty — which reads as a broken
datasource and is really a link that was never given anything to run.

Rebuilt as a plain external URL on the proven `panes` schema. Still empty. The
cause was visible only by reading the stored value back from
`/api/datasources/uid/projecta-loki`:

```
expr: {container="projecta-flask"} | json | request_id=""
```

**Grafana expands `$VAR` and `${VAR}` in provisioning YAML from the environment
before parsing the file.** `${__value.raw}` is not an environment variable, so
it expanded to nothing and the datasource was provisioned with a query matching
the empty string. `$$` is the documented escape. Dashboard JSON is *not*
interpolated this way, which is why `${__from}` and `${__to}` in the error-rate
panel worked untouched — same syntax, two files, two different rules, and no
error message from either.

With `$${__value.raw}`, clicking the link on a failing line runs:

```
{container="projecta-flask"} | json | request_id="loadgen-112000-385"
```

and returns **exactly two lines**:

```
11:22:29.962  "event": "http_request", "status": 400, "duration_ms": 1.09
11:22:29.961  "event": "bad_request",  "content_type": "text/plain"
```

One says how the request ended, the other says why. Three clicks from the
error-rate graph, no shell, no grep — which is 7.9, and the sentence the sprint
was for.

**The lesson worth repeating at review:** all three failures were silent. A link
that runs an empty query, a provisioning variable that expands to nothing, a
datasource stored with a broken expression — none of them logged anything, and
the UI looked plausible in each case. Reading the value back from the API is
what found it. That is the same argument as the `act_runner` dynamic matrix in
ADR-0005: the dangerous failures are the ones that report success.

Time the run and record it: from the first malformed request to reading the
`request_id` off the screen took `______` seconds. That number is the Sprint 3
equivalent of the ~37-second outage window — a measurement, not an estimate.

Still blank as of 2026-08-11, and left blank rather than filled in from memory.
The pivot itself is verified in §7; what is unmeasured is how long it takes a
person to walk it. ADR-0006 says the same thing about Loki's query latency: this
stack is cheap and the pivot works, both as numbers, and *fast* is not a number
yet.

---

## 8 — CI and CD still work

Nothing above touches the pipeline, but the app changed and the image changed.

```bash
git push gitea feature/sprint-3-observability
```

| Check | Passed when | Result |
|---|---|:--:|
| 8.1 Pipeline green on the feature branch | All gates pass; no image pushed, because `ships=false` | ✅ |
| 8.2 No step hit a timeout | Every step finishes well inside the bound `ci.yml` gives it | ✅ |
| 8.3 Deploy still smoke-tests clean | After merge to `release/sprint3`, CD runs and the smoke test passes | ✅ |
| 8.4 Idempotence holds | Second deploy of the same SHA → `changed=0` | ✅ |

**Run 2026-08-08, Gitea run #74** — `Merge pull request #38`, `release/sprint3`,
both jobs green in 1m46s total.

**8.2 — the bounds are not close to binding.** `ci.yml` carries twenty
step-level `timeout-minutes` and no job-level one, the tightest being 2m. The
whole `build-test-push` job took **1m17s** and `deploy` **26s** — each job
finished in less wall-clock time than the smallest single-step budget it
contains, so no individual step came near its limit. That is the honest reading
of a green run, and it is also the uninteresting one: these timeouts are not
tuned to the work, they are there to stop a hung step occupying a capacity-1
runner forever. The number worth watching is Trivy's 10m, because it is the step
whose duration depends on something outside this repository.

Run #73 on the same branch — the observability merge, before `timeout-minutes`
existed — took 38s and 24s against #74's 1m17s and 26s. The build job took twice
as long, and it is worth being clear that `timeout-minutes` cannot be the cause:
a bound kills a step, it does not slow one down. The difference is more likely
Docker layer cache state or a Trivy database refresh between the two runs. Not
investigated, and recorded here as unexplained rather than waved away, because a
build that doubles for reasons nobody checked is how a capacity-1 runner becomes
a bottleneck later.

**8.3 — CD deployed what CI built.** The `deploy` job in run #74 completed in
26s. `projecta-flask` reports:

```bash
docker inspect projecta-flask --format '{{index .Config.Labels "version"}}'
ed19d737d704ed01b4526955a56b396c9a7ba734
```

That is `release/sprint3`'s tip exactly — the artefact running is the one the
pipeline tested, not a rebuild. Ansible's own pre-flight play agrees:
`ok=9 changed=0 failed=0`, network `projecta-platform` present, Docker 29.6.1
with 11 containers.

**8.4 — the second deploy changed nothing.**

```
ansible-playbook playbooks/deploy.yml -e app_version=ed19d737d704ed01b4526955a56b396c9a7ba734

PLAY RECAP
docker-host : ok=11  changed=0  unreachable=0  failed=0
```

Eleven tasks, **zero changed**. The image pull, the container run and all five
smoke tasks — health, readiness, a valid echo, the payload assertion, and the
wrong-`Content-Type`-returns-400 assertion — each reported `ok` without
modifying anything. Re-running the deploy of a version already deployed is a
no-op, which is the property that makes the rollback drill safe to rehearse.

**8.1 — the ref gate, shown as a difference rather than asserted.** A
release-branch run cannot demonstrate this, because there `ships` is true and
pushing the image is the expected behaviour. The evidence has to come from a
feature branch. Gitea run **#75**, `feature/sprint-3-section-8-evidence`,
2026-08-08:

| Run | Branch | `build-test-push` | `deploy` |
|---|---|---|---|
| #74 | `release/sprint3` | 1m17s ✅ | 26s ✅ |
| #75 | `feature/sprint-3-section-8-evidence` | 40s ✅ | **0s, skipped** |

Every gate ran on the feature branch — Ruff, hadolint, pytest at the coverage
threshold, ansible-lint, the image build, the container health wait, the network
check, Trivy — and then the pipeline declined to deploy. The `deploy` job is
gated on `needs.build-test-push.outputs.ships == 'true'`, so a skip at 0s is
direct evidence that `ships` evaluated false. **Push Docker image** is gated on
the same `steps.ref_gate.outputs.ships`, so it cannot have run either; that step
was not opened individually, and the claim rests on the two sharing one output
rather than on having watched both.

This is the ref gate ADR-0005 describes, and the reason it is a POSIX shell
`case` rather than a `startsWith()` expression: the spike found `act_runner`'s
expression support unreliable, and a gate that silently evaluates true would
push an untested image from a feature branch without anything reporting an
error.

---

## Once this is all ✅ — done 2026-08-11

Only then update the status tables. The rows to change:

- ✅ `PLAN.md` Phase 1 — the two ⬜ items, JSON logging and `/metrics`
- ✅ `PLAN.md` Phase 5 — Observability
- ✅ `PLAN.md` §3 — milestone **M3**
- ✅ `PLAN.md` §4 — the two P0 rows
- ✅ `README.md` — the Sprint 3 row and the ⬜ observability rows
- ✅ `docs/adr/0006` and `0007` — **checked, nothing to delete.** This line
  anticipated provisional paragraphs that would stop being true. They do not
  exist. What 0006 actually carries is narrower and still accurate: the
  single-UI claim is verified in §7, and what remains unmeasured is Loki's
  *query latency under load*, which this sprint never measured and should not
  now pretend to have. 0007's "a rule that will be tested" is a statement about
  the next endpoint someone adds, not about this sprint. Both stand as written

Those edits were deliberately **not** in the observability commit. The branch
ships the capability; the status changes when the capability has been seen to
work. Making both in one commit is how a board starts lying.

**What that separation actually cost, recorded because it is the interesting
part.** The capability landed on 2026-08-08 and the tables were corrected on
2026-08-11. For three days the documentation *understated* the project: the
`README.md` a reader opens first said Sprint 3 was ⬜ Planned while sections 4
through 7 of this file were already ✅ against real evidence. Separating the
commits is still right — a status that changes with the code is a status nobody
can trust — but the second commit has to actually follow, and here it did not
until a demo forced it. The rule is unchanged; the Definition of Done now has
to include it rather than assume it.

**One finding came out of the correction pass itself.** The error-rate panel
was drawing green across a 96% spike — coloured from the classic palette rather
than its thresholds, no threshold line rendered, and a red step at 0.2 while the
alert rule fires at 0.1. Section 7 marked the incident ✅ and was right about
every claim it made; it simply never asserted anything about the panel's
colour, so nothing was wrong here and nothing had to be withdrawn. It was found
by photographing the panel for the review. Fixed in
`platform/observability/grafana/dashboards/app-golden-signals.json` the same
day, reasoning kept in the panel description.
