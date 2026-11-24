import os
import re
import sys
import tempfile
import time
from pathlib import Path

survey_id, number, prompts, teller = sys.argv[1:]

if not re.fullmatch(r"PJSIP/[0-9]+", teller):
    teller = "unknown"

if not re.fullmatch(r"\d+\.\d+", survey_id):
    raise SystemExit("Unexpected survey ID")
if not re.fullmatch(r"100[12]|110[12]", number):
    raise SystemExit("Unexpected callback extension")
if prompts not in {"ecng4308", "ecng4308/ar", "ecng4308/fr"}:
    raise SystemExit("Unexpected prompt directory")

spool = Path("/var/spool/asterisk")
destination = spool / "outgoing" / f"ecng4308-survey-{survey_id}.call"

with tempfile.NamedTemporaryFile(
    mode="w", dir=spool / "ecng4308-survey", delete=False
) as call_file:
    staged = Path(call_file.name)
    call_file.write(
        f"Channel: PJSIP/{number}\n"
        "MaxRetries: 0\n"
        "WaitTime: 25\n"
        "Context: ecng4308-survey\n"
        "Extension: s\n"
        "Priority: 1\n"
        f"Setvar: ECNG_SURVEY_ID={survey_id}\n"
        f"Setvar: ECNG_SURVEY_PROMPTS={prompts}\n"
        f"Setvar: ECNG_SURVEY_TELLER={teller}\n"
    )

try:
    due = time.time() + 15
    os.utime(staged, (due, due))
    os.replace(staged, destination)
finally:
    staged.unlink(missing_ok=True)
