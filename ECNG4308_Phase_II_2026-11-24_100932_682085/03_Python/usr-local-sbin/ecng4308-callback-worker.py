import re
import subprocess
import time

REQUEST = re.compile(
    r"^/ecng4308-callback/(\d+\.\d+)\s*:\s*"
    r"(ecng4308-retail(?:-ar|-fr)?)\|(100[12]|110[12])\s*$",
    re.MULTILINE,
)

QUEUE_HEADER = re.compile(r"^(\S+) has (\d+) calls\b")
PJSIP_MEMBER = re.compile(r"\bPJSIP/(\d+)(?=[\s)]|$)")


def cli(command, timeout=10):
    return subprocess.check_output(
        ["asterisk", "-rx", command], text=True, timeout=timeout
    )


def queue_snapshot():
    waiting, idle = {}, {}
    queue = None
    raw = cli("queue show")
    output = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", raw)

    for line in output.splitlines():
        line = " ".join(line.split())
        header = re.match(r"^(\S+) has (\d+) calls?\b", line)

        if header:
            queue = header[1]
            waiting[queue] = int(header[2])
            idle[queue] = []
        elif line.lower().startswith(("callers:", "no callers")):
            queue = None
        elif queue is not None:
            member = re.search(r"\bPJSIP/(\d+)(?=[\s)]|$)", line)
            status = line.lower()
            if member and "(not in use)" in status and "(paused" not in status:
                idle[queue].append(member[1])

    return waiting, idle

retry_at = {}
print("Watching retail queues for callbacks", flush=True)

while True:
    try:
        pending = REQUEST.findall(cli("database show ecng4308-callback"))
        pending.sort(key=lambda item: tuple(map(int, item[0].split("."))))
        retry_at = {
            request_id: retry_at[request_id]
            for request_id, _, _ in pending
            if request_id in retry_at
        }

        if pending:
            waiting, idle = queue_snapshot()
            emergency_waiting = any(
                count for queue, count in waiting.items()
                if queue.startswith("ecng4308-emergency")
            )

            for request_id, queue, _ in pending:
                if emergency_waiting or waiting.get(queue) != 0:
                    continue
                if not idle.get(queue) or time.monotonic() < retry_at.get(request_id, 0):
                    continue

                teller = idle[queue][0]
                retry_at[request_id] = time.monotonic() + 90
                print(f"Starting callback {request_id} with teller {teller}", flush=True)
                try:
                    result = cli(
                        f"channel originate PJSIP/{teller} extension "
                        f"{request_id}@ecng4308-callback-dispatch",
                        timeout=40,
                    )
                    if result.strip():
                        print(result.strip(), flush=True)
                finally:
                    # Allow both phones time to ring before launching another attempt.
                    time.sleep(60)
                break

    except (subprocess.SubprocessError, OSError) as error:
        print(f"Asterisk command failed: {error}", flush=True)

    time.sleep(2)
