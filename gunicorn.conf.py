"""Gunicorn configuration — exists for the two hooks, not for the settings.

The bind, worker and thread values could stay on the command line where they
were. They moved here because `prometheus_client`'s multiprocess mode needs
lifecycle hooks that a CMD cannot express, and splitting the runtime
configuration across two places would be worse than moving all of it.
"""

import os
import shutil

from prometheus_client import multiprocess

bind = "0.0.0.0:8000"
workers = 2
threads = 4

# stdout, one JSON object per line, formatted by app.logging_config. Gunicorn's
# own error logger is re-pointed at that formatter when the application module
# is imported.
errorlog = "-"

# Off, deliberately. `after_request` in app.py already emits a structured record
# for every request with the request_id, the route template and the duration
# attached. Leaving this on would produce a second, poorer line for the same
# event, and every rate derived from logs would be double-counted. The cost is
# stated in app/logging_config.py: a request malformed enough that gunicorn
# rejects it before Flask sees it is now logged by neither.
#
# **This setting alone does not do it, and that is not obvious.** Gunicorn's
# Logger.access() begins:
#
#     if not (self.cfg.accesslog or self.cfg.logconfig
#             or self.cfg.logconfig_dict or ...):
#         return
#
# so defining logconfig_dict below re-enables access logging that accesslog =
# None had switched off. Found on 2026-08-06, by the check that was written to
# catch the opposite problem: the fix for the arbiter's plain-text start-up
# lines quietly restored the duplicate access line those lines were fixed
# alongside. The NullHandler on gunicorn.access in logconfig_dict is what
# actually silences it — accesslog stays here because it is the setting anyone
# looking for this behaviour will search for first, and finding it set to None
# with no explanation would be worse than not finding it at all.
accesslog = None

# The arbiter's own log lines — "Starting gunicorn", "Listening at", "Booting
# worker" — are emitted before any worker exists and therefore before
# app.logging_config.configure_logging() has ever run. Calling that function
# from the application module only ever reaches the workers, so the first six
# lines of every container's log stayed plain text while every request line was
# JSON. Alloy tolerates the mix (a non-JSON line fails stage.json and passes
# through unparsed) but "mostly structured" is not a format, and the claim in
# logging_config.py that gunicorn's loggers are re-pointed was only half true.
#
# logconfig_dict is gunicorn's supported hook for this: it is handed to
# logging.config.dictConfig() inside Logger.setup(), which runs in the arbiter
# before the first line is written. Gunicorn shallow-merges this over its own
# CONFIG_DEFAULTS, so every key it would otherwise supply has to be present
# here — hence the handler and root entries that look redundant next to
# configure_logging().
#
# configure_logging() stays. It is what makes `flask run`, `pytest` and a bare
# `python -c "import app.app"` produce the same format, none of which involve
# gunicorn. Both paths install an equivalent handler by replacement rather than
# appending, so running both cannot double a line.
logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "app.logging_config.JsonFormatter"},
    },
    "filters": {
        "request_id": {"()": "app.logging_config.RequestIdFilter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
            "stream": "ext://sys.stdout",
        },
        # Where gunicorn's access records go to die. An explicit NullHandler
        # rather than an empty handler list: a logger with no handlers and
        # propagate=False falls through to logging.lastResort, which happens to
        # drop INFO because its own level is WARNING. That would work, and it
        # would work by coincidence — one changed level away from access lines
        # reappearing on stderr with nobody having touched this file.
        "devnull": {"class": "logging.NullHandler"},
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "gunicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        # Silenced, not formatted. See the accesslog note above: gunicorn emits
        # these records because logconfig_dict exists at all, so the only place
        # left to stop them is here.
        "gunicorn.access": {
            "level": "INFO",
            "handlers": ["devnull"],
            "propagate": False,
        },
    },
}


def on_starting(server):
    """Empty the multiprocess directory before any worker starts.

    The .db files in it are per-PID and outlive the process that wrote them.
    Restart the container and yesterday's dead workers are still counted, so
    every counter appears to jump on deploy. The library's own documentation
    calls for clearing the directory on startup; this is that, in the one place
    guaranteed to run before a worker exists.
    """
    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not path:
        return
    shutil.rmtree(path, ignore_errors=True)
    os.makedirs(path, exist_ok=True)
    server.log.info("cleared PROMETHEUS_MULTIPROC_DIR at %s", path)


def child_exit(server, worker):
    """Reap a dead worker's metric files.

    Without this, a worker that crashes and is replaced leaves its counters
    behind forever, and the aggregated total keeps including a process that no
    longer serves traffic. Gunicorn is the only component that knows a worker
    died, so it is the only place this can be done.
    """
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(worker.pid)
