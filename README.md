# VoIP Banking Call Center and PBX

An Asterisk banking call center built for **ECNG 4308 · Telecommunication Systems, Fall 2026** at The American University in Cairo. Customers dial **3000** from Linphone and use a multilingual IVR. Employees use the same PBX for internal calls and controlled customer transfers.

**Team:** Abdel Rahman El Helw and Kareem Elrokh  
**Supervisor:** Dr. Yasser Gadallah

## What the system does

- **Multilingual IVR.** Arabic, English, and French prompts guide customers through card/PIN authentication, account balance, prerecorded FAQs, and teller routing. Prospective customers go straight to a dedicated agent. The audio prompts were generated using AI text-to-speech and are played from local files.
- **Teller queues.** Retail callers reach agents for their selected language. Corporate calls go to a dedicated teller. Lost or stolen card calls receive priority when competing with normal calls for a shared teller.
- **Internal PBX and restricted transfers.** Employee dialing is controlled by role. On a live customer call, the teller can transfer to Technical Support or the Call Center Manager. Department managers and the CEO are outside that transfer list. Only managers can dial the CEO directly.
- **Congestion callback.** Waiting retail callers can use their registered extension or confirm a different lab extension. The worker rings an idle teller first, then calls the confirmed customer destination after the teller answers.
- **Satisfaction survey.** After an opted-in teller conversation ends, Asterisk schedules a follow-up call. The customer enters a rating from 1 to 5, and the result is stored with the answering teller.
- **Recording and call history.** Calls to 3000 are recorded. Internal conversation recording can be enabled in the dialplan. Call detail records, queue events, recordings, and survey results help trace a call.
- **Feature 10 · Automated banking alerts.** A low balance or repeated wrong PINs on the same known account can trigger an agent-first call through extension 2201. The system checks that the agent is idle before originating the alert.

**Bonus work:** Intelligent Call Center Analysis and Voice Quality Monitoring dashboards. The design report describes their purpose and data sources. Dashboard source code has its own export folder when supplied.

## Extension directory

| Extension | Role |
|---|---|
| 3000 | Customer IVR |
| 1001, 1002, 1101, 1102 | Lab customer endpoints |
| 2101, 2121, 2122 | English retail tellers |
| 2111–2113 | Arabic retail tellers |
| 2131–2133 | French retail tellers |
| 2102 | Corporate teller |
| 2103 | Prospective-customer agent |
| 2201 | Feature 10 alert agent |
| 2301 | Technical Support |
| 2401 | Call Center Manager |
| 2402, 2403 | Department managers |
| 2501, 2502 | Bank staff |
| 2900 | CEO |

## Repository layout

The Phase II export uses this directory structure. Run the setup commands from the folder containing these directories.

```text
Report/                    Report, architecture, and operating procedures
Asterisk/etc/asterisk/     Dialplan, PJSIP, queues, and supporting configuration
Python/agi-bin/            Customer authentication AGI
Python/usr-local-sbin/     Congestion callback worker and survey scheduler
Database/                  SQLite demo customer database
Soundtracks/               Prerecorded IVR prompts and digits
```

## Run on Ubuntu under WSL

The lab uses one **dedicated Windows PC as the server**, running Asterisk 22 in Ubuntu under WSL and managed through the VS Code WSL terminal. Use at least four separate phones or PCs running Linphone to demonstrate simultaneous customer, teller, and alert-agent calls. The clients must be able to reach the server on the LAN. The demo uses **SIP over UDP port 5062**, PCMU audio, and RFC 4733 keypad events.

### 1. Install the exported project files

Start with Asterisk, Python 3, and the standard Asterisk sound package installed on the WSL server. The paths and the `asterisk` service account below match the team's server setup. Use only fictional lab data and demo accounts.

```bash
backup_stamp=$(date +%Y%m%d-%H%M%S)
sudo cp -a /etc/asterisk "/etc/asterisk.bak-$backup_stamp"
if sudo test -f /usr/share/asterisk/agi-bin/ecng4308.sqlite; then
  sudo cp -a /usr/share/asterisk/agi-bin/ecng4308.sqlite \
    "/usr/share/asterisk/agi-bin/ecng4308.sqlite.bak-$backup_stamp"
fi
sudo cp -a 02_Asterisk/etc/asterisk/. /etc/asterisk/

sudo install -d /usr/share/asterisk/agi-bin /usr/share/asterisk/sounds /usr/local/sbin
sudo install -m 0755 03_Python/agi-bin/ecng4308_auth.py /usr/share/asterisk/agi-bin/
sudo install -m 0755 03_Python/usr-local-sbin/ecng4308-*.py /usr/local/sbin/
sudo install -o root -g asterisk -m 0640 \
  04_Database/ecng4308.sqlite /usr/share/asterisk/agi-bin/ecng4308.sqlite
sudo cp -r 05_Sounds/. /usr/share/asterisk/sounds/
sudo install -d -o asterisk -g asterisk -m 0750 /var/spool/asterisk/ecng4308-survey
```

Start Asterisk if it is stopped. If it is already running, reload the configuration with `sudo asterisk -rx 'core reload'`. Restart Asterisk if the PJSIP transport settings changed. Then check that the dialplan and queues are loaded:

```bash
sudo asterisk -rx 'dialplan show 3000@ecng4308-customers'
sudo asterisk -rx 'queue show'
sudo asterisk -rx 'pjsip show contacts'
```

### 2. Register the Linphone clients

Use the server's LAN address, UDP port `5062`, and each extension's configured SIP credentials. For a four-device demo, register two customers such as `1101` and `1102`, teller `2101`, and alert agent `2201`. Assign additional devices for transfer and concurrent-queue tests as needed. The customer card number and PIN are separate from Linphone's SIP login.

### 3. Start the congestion callback worker

Leave this running on the server while testing automatic congestion callbacks:

```bash
sudo flock -n /run/lock/ecng4308-callback-worker.lock \
  python3 -u /usr/local/sbin/ecng4308-callback-worker.py
```

The survey scheduler is called by the dialplan at hangup. Asterisk places the scheduled call from its outgoing spool.

## Demo checklist

| Test | Expected behavior |
|---|---|
| Dial `3000` | Choose Arabic (`1`), English (`2`), or French (`3`). Choose existing customer (`1`) or prospective customer (`2`). |
| Authenticate as a demo customer | Enter the card and PIN, each followed by `#`. Test balance (`1`), FAQ (`2`), and teller services (`3`). |
| Join a teller queue | Select retail (`1`), corporate (`2`), or lost/stolen card (`3`). With a shared teller busy, verify that the emergency caller is served first when the teller becomes free. |
| Transfer a connected customer call | On the teller's in-call keypad, use the configured blind-transfer key (`#` on the lab server). Verify that `2301` and `2401` ring and that `2402`, `2403`, and `2900` are denied. |
| Request a retail callback | While waiting, press `1` for the registered number or `2` for a confirmed alternate lab extension. Free a teller, answer the teller phone first, then answer the customer phone. |
| Complete an opted-in teller call | Answer the survey call roughly 15 seconds after hangup and enter a score from `1` to `5`. Confirm the stored score and teller. |
| Trigger Feature 10 | Test the below-threshold balance and the lab's three-wrong-PIN condition on a recognized demo account. With `2201` idle, answer the agent leg first, then the registered customer's phone. Repeat with the agent busy to verify the availability condition. |

## Inspect call evidence

```bash
sudo asterisk -rx 'database show ecng4308-callback'
sudo asterisk -rx 'database show ecng4308-survey-results'
sudo ls -lt /var/spool/asterisk/monitor/ | head
sudo tail -n 10 /var/log/asterisk/cdr-csv/Master.csv
sudo tail -n 10 /var/log/asterisk/queue_log
```

Set `ECNG_RECORD_INTERNAL=yes` under `[globals]` in the live dialplan and reload it to enable internal call recording. The CDR and queue log paths assume the team's CSV and queue logging configuration is active.

---

*P.S. This README was drafted to aid you through working with these files with the assistance of AI and reviewed by the repository maintainer.*
