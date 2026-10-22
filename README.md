# obd2-emulator

SAE J1979 / OBD-II **light-vehicle ECU emulator** for fleet, telematics, and ELM327 stack QA.
Simulate live PIDs, stored DTCs, VIN/CALID, and ISO-TP responses on a **virtual** or **physical** CAN bus—no vehicle required.

Built with **python-can**, **can-isotp**, and **NiceGUI**.

**Requirements:** Python **3.11+** · Windows, Linux, or macOS · a browser for the GUI (Chrome, Edge, Firefox, or Safari)

### What you get (v0.1)

| Area | Capability |
|------|------------|
| **Bus** | Real hardware detect or Virtual (`vcan0` / `vcan1` / `vcan2`) · START / STOP / RESET · TX / RX / load |
| **Live data** | Mode `$01` — full Annex B catalog (167 PIDs) + support bitmasks + runtime edit |
| **Diagnostics** | Mode `$03` stored DTCs (SF/MF) · Mode `$04` clear |
| **Vehicle** | Mode `$09` — InfoType `$00` · `$02` VIN · `$04` CALID |
| **UI** | Python CLI (automation) or NiceGUI localhost (default `http://127.0.0.1:8080`) |

Transport: ISO 15765-4 (functional `0x7DF` + physical `0x7E0`→`0x7E8`, plus 29-bit). Not a full J1979DA suite yet (freeze frames / Modes `$02`/`$05`–`$0A` still on the roadmap).

---

## 1. Clone and set up

Run every command from the **repository root** (`obd2-emulator`), not from the inner `obd2_emulator` package folder. That root is where `pyproject.toml` and `examples/` live.

Pick **one** shell and follow its block end-to-end.

### Windows PowerShell

```powershell
git clone https://github.com/Embedded-Verse/obd2-emulator.git
cd obd2-emulator

python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation fails with `running scripts is disabled`:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Or skip Activate and call the venv Python by full path in later steps, e.g. `.\.venv\Scripts\python.exe -m pip install …`.

### Windows Command Prompt (cmd.exe)

```bat
git clone https://github.com/Embedded-Verse/obd2-emulator.git
cd obd2-emulator

python -m venv .venv
.venv\Scripts\activate.bat
```

### Linux / macOS

```bash
git clone https://github.com/Embedded-Verse/obd2-emulator.git
cd obd2-emulator

python3 -m venv .venv
source .venv/bin/activate
```

### Docker / CI (headless)

Use the same install steps inside the image or job (Python 3.11+). Prefer **Virtual** mode for smoke tests—no USB CAN required. Example pattern:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m obd2_emulator --config examples/ecu.toml --mode virtual --channel 1 --no-start
```

For the **localhost GUI** in a container, publish the port and either open a browser on the host or use `--host 0.0.0.0` (bind carefully—default remains `127.0.0.1` for local-only use):

```bash
python -m obd2_emulator --gui --config examples/ecu.toml --host 0.0.0.0 --port 8080 --no-browser
# then browse http://localhost:8080 on the host (map -p 8080:8080)
```

---

## 2. Install

Stay in the repository root with the venv **activated** (your prompt should show `(.venv)`).

### Quick start (Virtual bus — enough to try CLI + GUI)

**Windows PowerShell**

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

**Windows Command Prompt**

```bat
python -m pip install --upgrade pip
python -m pip install -e .
```

**Linux / macOS**

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

This installs the app plus **python-can**, **python-can-candle**, **can-isotp**, **nicegui**, **libusb-package**, and **pyserial**. On **Windows**, **pywin32** is also installed. You can run Virtual Emulation immediately—no CAN adapter required.

### Full install (Real Hardware adapters)

Use this if you will connect Peak, Vector, candleLight, etc. Vendor **OS drivers** are still required for those devices.

**Windows PowerShell**

```powershell
python -m pip install --upgrade pip
python -m pip install -e . "python-can[gs-usb,serial,candle,pcan,neovi,canalystii,nixnet,seeedstudio,cvector,remote,sontheim,canine,zlgcan,viewer,mf4,multicast,pywin32]"
```

**Windows Command Prompt**

```bat
python -m pip install --upgrade pip && python -m pip install -e . "python-can[gs-usb,serial,candle,pcan,neovi,canalystii,nixnet,seeedstudio,cvector,remote,sontheim,canine,zlgcan,viewer,mf4,multicast,pywin32]"
```

**Linux / macOS**

```bash
python -m pip install --upgrade pip && python -m pip install -e . "python-can[gs-usb,serial,candle,pcan,neovi,canalystii,nixnet,seeedstudio,cvector,remote,sontheim,canine,zlgcan,viewer,mf4,multicast]"
```

Optional CANtact (needs [Rust](https://rustup.rs)):

```bash
python -m pip install "python-can[cantact]"
```

---

## 3. Run — CLI

With the venv activated and still at the **repository root**:

```bash
python -m obd2_emulator --config examples/ecu.toml
```

Uses Virtual channel `vcan0` at 500 kbit/s by default (see `examples/ecu.toml`). On START the ECU answers OBD requests on ISO-TP.

### Discover channels (Virtual or Real)

List adapters, then pass the **number** to `--channel`:

```bash
python -m obd2_emulator --list-channels --mode virtual
python -m obd2_emulator --list-channels --mode real
```

Example (Real hardware — pick channel **1** from the list):

```bash
python -m obd2_emulator --list-channels --mode real
python -m obd2_emulator --config examples/ecu.toml --mode real --channel 1 --bitrate 500000
```

#### From scratch — Real Hardware (Windows PowerShell)

```powershell
git clone https://github.com/Embedded-Verse/obd2-emulator.git
cd obd2-emulator

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e . "python-can[gs-usb,serial,candle,pcan,neovi,canalystii,nixnet,seeedstudio,cvector,remote,sontheim,canine,zlgcan,viewer,mf4,multicast,pywin32]"

python -m obd2_emulator --list-channels --mode real
python -m obd2_emulator --config examples/ecu.toml --mode real --channel 1 --bitrate 500000
```

#### From scratch — Real Hardware (Windows Command Prompt)

```bat
git clone https://github.com/Embedded-Verse/obd2-emulator.git
cd obd2-emulator

python -m venv .venv
.venv\Scripts\activate.bat

python -m pip install --upgrade pip && python -m pip install -e . "python-can[gs-usb,serial,candle,pcan,neovi,canalystii,nixnet,seeedstudio,cvector,remote,sontheim,canine,zlgcan,viewer,mf4,multicast,pywin32]"

python -m obd2_emulator --list-channels --mode real
python -m obd2_emulator --config examples/ecu.toml --mode real --channel 1 --bitrate 500000
```

#### From scratch — Real Hardware (Linux / macOS)

```bash
git clone https://github.com/Embedded-Verse/obd2-emulator.git
cd obd2-emulator

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e . "python-can[gs-usb,serial,candle,pcan,neovi,canalystii,nixnet,seeedstudio,cvector,remote,sontheim,canine,zlgcan,viewer,mf4,multicast]"

python -m obd2_emulator --list-channels --mode real
python -m obd2_emulator --config examples/ecu.toml --mode real --channel 1 --bitrate 500000
```

On your PC that might look like:

```text
Available Real CAN channels (2):

  #   Adapter
  --  -----------------------------------------------
  1   candleLight  (serial ...20313730)
  2   candleLight  (serial ...20383032)

Example:
  python -m obd2_emulator --config examples/ecu.toml --mode real --channel 1 --bitrate 500000
```

So `--channel 1` means the first listed adapter. For Virtual mode you can also use names `vcan0`, `vcan1`, `vcan2`.

### Other launch examples

```bash
python -m obd2_emulator --config examples/ecu.toml --mode virtual --channel vcan0 --bitrate 500000
python -m obd2_emulator --config examples/ecu.toml --mode virtual --channel 1 --bitrate 250000
python -m obd2_emulator --config examples/ecu.toml --no-start
```

### At the `>` prompt

```text
channels
channels real
channel 1
mode virtual
bitrate 500000
status
pid meta
pid get 0C
pid set engine_rpm 2500
dtc add P0301
dtc list
dtc clear
vin get
vin set 1HGCM82633A004352
calid get
calid set OBD2EMU-CAL-0001
stop
start
reset
help
quit
```

| Command | Meaning |
|---------|---------|
| `channels [real\|virtual]` | List adapters; note the **#** to use with `--channel` / `channel` |
| `channel [N]` | Show current channel or select by number |
| `mode [real\|virtual]` | Show or change emulation mode |
| `bitrate [Hz]` | Show or set bitrate (`125000`…`1000000`) |
| `pid meta` / `pid get` / `pid set` | Catalog / read / change live Mode `$01` values |
| `dtc list` / `add` / `remove` / `clear` | Mode `$03` / `$04` diagnostics |
| `vin` / `calid` | Mode `$09` vehicle info |
| `status` / `stop` / `start` / `reset` / `quit` | Session control |

`channels` and the CLI flags are intended for automation (Docker/CI/ELM327 benches): discover adapters, then pin `--mode` / `--channel 1` / `--bitrate` in the process command or TOML.

---

## 4. Run — GUI (localhost)

```bash
python -m obd2_emulator --gui
```

The default browser opens automatically at `http://127.0.0.1:8080`.

Custom host/port:

```bash
python -m obd2_emulator --gui --host 127.0.0.1 --port 8090
```

Use `--no-browser` to skip auto-open (useful in Docker or remote shells). In the UI, click **QUIT** to stop the server and return to the shell.

Optional preset from TOML:

```bash
python -m obd2_emulator --gui --config examples/ecu.toml
```

Typical workflow:

1. Choose **Virtual Emulation** (no hardware) or **Real Hardware** (adapters attached)
2. Select channel and bitrate (**500 kbit/s** common for OBD CAN; **250 kbit/s** for some ELM protocols)
3. Click **START** — ECU listens on functional + physical ISO-TP IDs
4. **Live** tab — edit PIDs / signals; values update on the next request
5. **Diagnostics** tab — add / clear DTCs (Mode `$03` / `$04`)
6. **Vehicle** tab — edit VIN / CALID (Mode `$09`)
7. Click **QUIT** (or Ctrl+C in the terminal) when finished so USB adapters are released

### Bus modes

| Mode | Channels | Hardware |
|------|----------|----------|
| **Virtual Emulation** | `vcan0`, `vcan1`, `vcan2` (python-can software bus) | Not required |
| **Real Hardware** | Detected adapters (e.g. candleLight, Vector VN1610, …) | Adapter must be connected; unplugged devices do not appear |

### Tips

- If port **8080** is already in use: `python -m obd2_emulator --gui --port 8090`
- Always stop with **QUIT** / `quit` / Ctrl+C so the process exits and CAN adapters unlock
- Virtual mode needs no CAN hardware and is the fastest way to verify the install
- ELM327 scanners often use **functional** `0x7DF` — the emulator answers that (and physical `0x7E0` / 29-bit)

---

## 5. Example config

See [`examples/ecu.toml`](examples/ecu.toml). Key fields:

```toml
[bus]
bitrate = 500000
request_id = 0x7E0
response_id = 0x7E8
mode = "virtual"          # "real" | "virtual"
# channel = "1"           # optional: number from --list-channels

[vehicle]
vin = "1HGCM82633A004352"
calid = "OBD2EMU-CAL-0001"

[live]
engine_rpm = 800.0
vehicle_speed_kph = 0.0
coolant_c = 90.0
throttle_pct = 0.0
mil_on = false
dtc_count = 0

# Optional demo DTCs (Mode $03)
# [[diagnostics.dtc]]
# code = "P0301"
# description = "Cylinder 1 Misfire"
```

---

## 6. Hardware notes

- Prefer **candleLight** (`candle` interface). VN1610 / Vector also appear in Real mode when drivers are installed.
- Always **STOP** or **QUIT** when finished — the emulator force-releases USB handles and settles before reopen so the bench is left unlocked.
- Typical ELM bench: emulator on candle #1 on the same CAN as an ELM327 (e.g. ESP32 UART). Emulator bitrate must match the protocol under test (often 500 kbit/s for ATSP6/7/0; 250 kbit/s for ATSP8/9).
- Addressing answered: **11-bit** RX `0x7DF` + `0x7E0` → TX `0x7E8`; **29-bit** RX `0x18DB33F1` + `0x18DA10F1` → TX `0x18DAF110`. Multi-frame replies after a functional request use the physical ISO-TP stack so Flow Control lands on `0x7E0`.

---

## 7. Supported services (current)

| Service | Capability |
|---------|------------|
| `$01` | **Full Annex B catalog** (167 PIDs `$00`–`$A9`, excl. reserved `$95`–`$97`) + support bitmasks + runtime edit |
| `$03` | Stored DTCs (0…N; ISO-TP SF/MF) |
| `$04` | Clear DTCs + affirmative `44` |
| `$09` | InfoType `$00` support · `$02` VIN · `$04` CALID |

Encodings follow the SAE J1979 Digital Annex (ISO 15765-4 message formats). GUI groups editable signals by virtual ECU (Powertrain / Fuel / Emissions); the wire format stays J1979-native.

CLI helpers: `pid meta` · `pid get 0C` · `pid set maf_gps 8.5`.

---

## License

MIT — see [LICENSE](LICENSE).
