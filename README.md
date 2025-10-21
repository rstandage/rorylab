# RoryLab - Mist API Network Management Scripts

A collection of Python scripts for managing and auditing Mist cloud network infrastructure. These scripts use the `mistrs` library for authentication and API interactions with the Mist cloud platform.

## Prerequisites

- Python 3.6+
- `mistrs` library (Mist API client)
- Valid Mist cloud credentials

## Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd rorylab   ```

## Analysis Scripts

### SAE Authentication Failure Analysis
**File:** `scripts/sae_auth_failure_analysis.py`

Analyzes SAE (Simultaneous Authentication of Equals) authentication failure events from Mist client event CSV exports. Provides comprehensive statistics on failure patterns, including:

- Site and access point distributions
- Client device patterns (including random MAC analysis)
- RSSI signal strength analysis
- Hourly and daily failure patterns  
- Status codes and failure reasons
- Band and SSID analysis

**Usage:**
```bash
python3 scripts/sae_auth_failure_analysis.py <csv_file> [-n TOP_N] [-o OUTPUT_FILE]
```

**Example:**
```bash
python3 scripts/sae_auth_failure_analysis.py "data/sae_failures.csv" -n 20 -o analysis_report.txt
```

### DNS Failure Analysis
**File:** `scripts/dns_failure_analysis.py`

Analyzes DNS failure events with similar comprehensive reporting capabilities for DNS-related connectivity issues.
