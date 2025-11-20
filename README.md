# RoryLab – Mist API automation scripts

Small, focused Python scripts to audit, report on, and operate Juniper Mist orgs. Most scripts authenticate interactively via the helper library `mistrs` and export CSV reports to `~/created_files`.

## Requirements

- Python 3.8+ (tested on macOS)
- Mist admin credentials with access to your org(s)
- Python package: `mistrs`

## Installation

1) Clone this repository
2) Create and activate a virtual environment
3) Install dependencies

Example (zsh/macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Notes
- Scripts prompt for Mist login and (for some) a 2FA/OTP code. If your `org_id` isn’t pre-set, you’ll be asked to paste it once.
- CSV outputs are written under `~/created_files` unless stated otherwise.
- `data/mistapi.yaml` is the Mist OpenAPI specification for reference; it’s not required to run the scripts.

## How to run

Run any script directly, for example:

```bash
python scripts/ap_audit.py
python scripts/client_audit.py --duration 7d
python scripts/dns_failure_analysis.py path/to/dns_failures.csv -n 20 -o analysis.txt
```

Most scripts are interactive and will guide you to select a site or confirm actions. Reporting scripts typically finish by writing a CSV and printing the file path.

## Script overview

- ap_audit.py
   - Exports Access Point inventory and status across the org: site, model, firmware, IP, uptime, and LLDP details (switch, port, port speed). Writes a CSV to `~/created_files`.

- assign_switch_role_ip.py
   - Interactive wizard to set a switch’s name, role, and static IP configuration (IP/netmask/gateway/DNS). Optionally associates the device with a site VLAN/network pulled from derived site settings.

- check_timeouts.py
   - Lists all orgs your token can access and shows each org's UI idle timeout. Outputs a simple table sorted by the longest timeout.

- client_audit.py
   - Exports Wi‑Fi client details seen over a time window (default 7d): hostname, IP, SSID, VLAN, last AP, manufacturer, device type/OS, random MAC flag, last seen. Supports `--duration`, `--limit`, and `--debug`.

- clone_org.py
   - Clones Mist organizations and creates admin invites for multiple users. Supports batch processing via CSV (`--csv file.csv`) or interactive mode for single users. Validates user-level token, prompts for source org ID, clones with custom names, and creates org_admin invites valid for 7 days. See `scripts/CLONE_ORG_README.md` for detailed documentation.

- create_msp.py
   - Creates a new MSP in Mist by name. Simple interactive prompt with a confirmation step.

- dns_failure_analysis.py
   - Offline analysis of a Mist client-events CSV filtered to DNS failures. Prints distributions for domains, DNS servers, sites, devices, VLANs, and hourly patterns; can export the analysis to a text file. Does not call the Mist API.

- error_tracker.py
   - Fetches device events (default: REPEATED_AUTH_FAILURES, last 24h), then groups and visualizes by site or AP using `mistrs.analyze_errors`. Optionally limit to top-N and save a PNG.

- find_discovered.py
   - Builds a report of “discovered switches” per site, including management address, model/version, AP connectivity/redundancy, and basic chassis info. Exports a CSV.

- key_audit.py
   - Exports API tokens (name, created/last-used, scope/role) for your org to CSV. Helpful for periodic key audits.

- license_expiry_graph.py
   - Retrieves license entitlements and details, prints a summary and highlights items expiring soon/expired, then writes a detailed CSV sorted by “days until expiry.”

- ping_hook.py
   - Lists org-level webhooks and lets you select one to send a test ping. Useful for validating webhook endpoints.

- ssid_audit.py
   - For a selected site and time window, analyzes SSID usage and configuration: unique clients, total connections, bands/protocols, top manufacturers/device types, VLANs observed, and key WLAN config (auth, VLAN, rate limits, portal/NAC). Exports a CSV.

- switch_audit.py
   - Switch inventory report: model, firmware, site, IP, uptime, cluster size, and online-since timestamp. Exports a CSV.

- upgrade_ap.py
   - Prompts for an AP MAC, shows details, confirms by name, then triggers a firmware upgrade to a target version (optional reboot).

## Tips and troubleshooting

- Authentication/OTP
   - Scripts are designed by default to use org tokens, to overide this use (otp=false) when requesting credentials

- Org selection
   - If `org_id` isn’t in your credentials, scripts will prompt for it once. You can reuse the same virtual environment across runs.

- Output location
   - If you don’t see a CSV, check `~/created_files` and your terminal for the exact path printed at the end of the run.

- Permissions
   - Mutating scripts (e.g., assign switch settings, upgrade AP, create MSP) require appropriate org/site admin privileges.

## Reference

- Mist OpenAPI spec: `data/mistapi.yaml`
- Primary helper library: `mistrs` (installed via requirements.txt)

If you need a new report or automation, open an issue with a short description and sample output you’d like to see.
