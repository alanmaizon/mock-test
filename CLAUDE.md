# AVASO L2 Desktop Support — Mock Test Builder

## Project goal

Build a CLI mock test application that simulates the AVASO / TestGorilla screening test for L2 desktop support roles. The app should let me practice unlimited times under realistic conditions, get scored, and review wrong answers with explanations.

## Test format to simulate

Based on the actual AVASO test:

- **5 sections:** EUC, Wi-Fi, Network, Server, English
- **Total time:** 50–60 minutes
- **Pass mark:** 75% overall
- **Question type:** multiple choice, 4 options each (A/B/C/D), single correct answer
- **Approximate question count:** 40–50 total, distributed across sections
- **Difficulty:** L2 desktop support level — practical troubleshooting, not architect-level theory

## Suggested section weights

| Section | Questions | Reasoning |
|---------|-----------|-----------|
| EUC | 12 | Largest real-world section: Windows, AD, Office 365, printers |
| Network | 10 | High-yield: OSI, TCP/IP, ports, commands, IP addressing |
| Wi-Fi | 6 | Smaller: frequencies, security, troubleshooting |
| Server | 8 | Mid-size: RAID, Windows Server roles, GPO, backups |
| English | 4 | Grammar, comprehension, business writing |
| **Total** | **40** | |

## Functional requirements

### Core features

1. **Question bank** stored in JSON or YAML for easy editing/expansion
2. **Section-by-section flow** — present questions one section at a time
3. **Timed sessions** — overall timer (configurable, default 60 min) visible during test
4. **No back navigation** by default (matches real test feel) — toggle option for review mode
5. **Score breakdown by section** at the end
6. **Wrong answer review** — show question, my answer, correct answer, and explanation
7. **Difficulty modes:**
   - `practice` — no timer, instant feedback after each question
   - `exam` — timed, full feedback only at end
   - `drill` — pick a single section, unlimited time, instant feedback

### Question schema

Each question should have:

```json
{
  "id": "net_001",
  "section": "network",
  "difficulty": "easy|medium|hard",
  "question": "A user reports their PC has IP address 169.254.78.22 and cannot access network resources. What is the most likely cause?",
  "options": {
    "A": "DNS misconfiguration",
    "B": "PC failed to obtain an IP from DHCP",
    "C": "Default gateway unreachable",
    "D": "User is on the wrong VLAN"
  },
  "correct": "B",
  "explanation": "169.254.x.x is APIPA — assigned by Windows when DHCP fails. Without a real IP, the PC has no gateway or DNS configured, so it cannot reach anything beyond the local link.",
  "topic": "DHCP/APIPA",
  "tags": ["dhcp", "apipa", "ip-addressing"]
}
```

### Topics to cover (for question bank generation)

**EUC (12 questions):**
- Windows 10/11 boot issues, Safe Mode, recovery options
- Active Directory: user accounts, password reset, account lockout
- Group Policy basics from end-user side
- Office 365: Outlook profile rebuild, OST vs PST, shared mailboxes
- Printer troubleshooting: spooler, drivers, stuck jobs
- BitLocker basics
- BSOD interpretation
- Windows command-line tools: `sfc`, `dism`, `chkdsk`, `gpupdate`
- Profile corruption, login issues
- Software install/uninstall issues

**Network (10 questions):**
- OSI model: layers, protocols at each layer, devices at each layer
- TCP vs UDP: differences, when each is used
- Common ports: 22, 25, 53, 80, 443, 445, 3389, 110, 143
- IP addressing: private ranges, APIPA, loopback, subnet basics
- DNS vs DHCP: function, troubleshooting
- Networking commands: `ipconfig`, `ping`, `tracert`, `nslookup`, `netstat`, `arp`
- VPN basics
- Collision vs broadcast domains
- Switches vs routers vs hubs

**Wi-Fi (6 questions):**
- 2.4 GHz vs 5 GHz: range, speed, interference, channels (1/6/11)
- 802.11 standards: b/g/n/ac/ax (Wi-Fi 4/5/6)
- WPA2 vs WPA3, why WEP is obsolete
- Common troubleshooting: weak signal, wrong password, DHCP exhaustion
- "Connected but no internet" diagnostic flow
- AP placement, SSID concepts

**Server (8 questions):**
- RAID 0/1/5/6/10: minimum disks, fault tolerance, use cases
- Windows Server roles: AD DS, DNS, DHCP, File Server, Print Server, IIS, Hyper-V
- Group Policy: order of application (LSDOU), `gpupdate`, `gpresult`
- Backup types: full, incremental, differential, 3-2-1 rule
- Server hardware: ECC RAM, hot-swap, redundant PSUs
- Remote management: iDRAC, iLO, RDP

**English (4 questions):**
- Grammar: subject-verb agreement, common confusions (their/there/they're, its/it's, affect/effect)
- Reading comprehension on a short IT-related passage
- Professional email tone for support tickets
- Concise rewriting

## Stretch features (build if time permits)

1. **Question randomization** — different question subset each run
2. **Adaptive difficulty** — if I get easy questions right, push harder ones
3. **Stats tracking** — save results across sessions, show weak topics
4. **Spaced repetition mode** — re-test wrong answers more often
5. **Export results** as a markdown file for review
6. **Webcam-on dummy mode** — open webcam during test (not required, just for realism conditioning)
7. **Tab-switch warnings** — log if I leave the terminal/window during a test

## Tech preferences

- **Language:** Python 3 (simple, readable, good CLI libraries)
- **CLI library:** `rich` or `textual` for nice formatting (optional but recommended)
- **Storage:** JSON or SQLite for question bank and session history
- **No web framework needed** — keep it terminal-based for speed
- **Single-file or small project structure** — easy to extend

## Suggested project structure

```
avaso_mock_test/
├── README.md
├── main.py                 # entry point, CLI args
├── test_engine.py          # question presentation, timing, scoring
├── question_bank/
│   ├── euc.json
│   ├── network.json
│   ├── wifi.json
│   ├── server.json
│   └── english.json
├── results/                # per-session score logs
└── requirements.txt
```

## What I want Claude Code to do

1. **Set up the project structure** — create the folders and skeleton files
2. **Write the test engine** — load questions, present them, time the test, score results
3. **Generate the initial question bank** — at least 60 questions across the 5 sections (more than enough for a 40-question test with randomization)
4. **Add the three modes** — `practice`, `exam`, `drill`
5. **Make wrong-answer review clear and useful** — full explanation for each missed question

## How I'll use this

I'll run `exam` mode to simulate the real test under timed conditions, then `drill` mode on whichever section I scored worst on, then `practice` mode for targeted weak topics. Once I'm consistently hitting 85%+ in `exam` mode, I'll know I'm ready for the real test.

---

**Start by:**

1. Creating the project structure
2. Building `test_engine.py` with the core flow
3. Generating the first 10–15 questions per section as a starting bank
4. Letting me run a quick smoke test before expanding the question count