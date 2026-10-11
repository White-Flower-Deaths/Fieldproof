import re
import pathlib

from app.enums import (
    CONCENTRATION_NOT_DETERMINABLE,
    DEMO_CITATION,
    DISCLAIMER,
    RESULT_STATUS,
)

ts = pathlib.Path("..", "frontend", "src", "lib", "constants.ts").read_text(encoding="utf-8")


def ts_const(name: str) -> str:
    m = re.search(name + r"\s*=\s*(.*?)\n\n", ts, re.S)
    assert m, name
    body = m.group(1)
    # prefer double-quoted segments (they may contain apostrophes)
    segments = re.findall(r'"([^"]*)"', body)
    if not segments:
        segments = re.findall(r"'([^']*)'", body)
    return "".join(segments)


statuses = re.search(r"RESULT_STATUSES = \[(.*?)\]", ts, re.S).group(1)
ts_status = tuple(re.findall(r"'([^']+)'", statuses))

checks = [
    ("DISCLAIMER", ts_const("DISCLAIMER") == DISCLAIMER),
    ("CONCENTRATION_NOTE", ts_const("CONCENTRATION_NOTE") == CONCENTRATION_NOT_DETERMINABLE),
    ("DEMO_CITATION", ts_const("DEMO_CITATION") == DEMO_CITATION),
    ("RESULT_STATUSES", ts_status == tuple(RESULT_STATUS)),
]
for name, ok in checks:
    print(f"{name:20} {'MATCH' if ok else 'MISMATCH'}")
print("OVERALL:", "MATCH" if all(ok for _, ok in checks) else "MISMATCH")
if not all(ok for _, ok in checks):
    print("ts DISCLAIMER:", repr(ts_const("DISCLAIMER")))
    print("py DISCLAIMER:", repr(DISCLAIMER))
    print("ts statuses:", ts_status)
    print("py statuses:", tuple(RESULT_STATUS))
