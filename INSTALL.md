<!-- v1.0 -->
# Vet Practice SQL Tester - Azure VM Installation Guide

## System Requirements (Azure VM)

| Component | Minimum | Recommended |
|---|---|---|
| Azure VM Size | B1s (1 vCPU, 1GB RAM) | B1ms (2 vCPU, 2GB RAM) |
| OS Image | Ubuntu 22.04 LTS (Azure Marketplace) | Ubuntu 22.04 LTS |
| Python | 3.8+ (pre-installed) | 3.11+ |
| Disk (OS) | 30GB Standard SSD | 30GB Standard SSD |
| Disk (baselines) | ~50KB per baseline (on OS disk) | Attach 1GB Data Disk for long-term retention |
| Network / NSG | SSH (port 22) inbound only; app on localhost:8000 | Same — no public HTTP port needed |
| Azure Region | Any region near your databases | Same region as DB for lowest latency |

### Dependencies

- **Flask** (web framework) - installed via pip
- **sqlite3** (built into Python) - demo mode only
- **Database driver** (production mode - choose one):
  - SQL Server / Azure SQL: `pyodbc`
  - PostgreSQL: `psycopg2-binary`
  - MySQL: `pymysql`
  - Oracle: `cx_Oracle`

## Where Data Is Stored

### Baseline Snapshots
Baselines (pre-deploy query results saved for comparison) are stored as JSON files on the Azure VM's OS disk.

**Default location:** `/opt/vet-sql-tester/baselines/`

This is controlled by the `VET_BASELINE_DIR` environment variable:
```bash
# Override the baseline storage directory
export VET_BASELINE_DIR=/data/baselines
```

Each baseline is a JSON file named after the label you give it when saving:
```
/opt/vet-sql-tester/baselines/pre_deploy_2026-09-18T12-30.json
/opt/vet-sql-tester/baselines/healthcare_plan_update.json
```

**Size per baseline:** ~50KB-500KB depending on query results (10 databases x N rows).

**Persistence on Azure:**
- Baselines on the OS disk survive VM reboots and restarts (Azure VM OS disks are persistent by default).
- If the VM is deleted and recreated, OS disk baselines are lost. For long-term retention across VM rebuilds, attach an Azure Data Disk and point `VET_BASELINE_DIR` to the mounted data disk path.
- Baselines can be shared between testers who SSH into the same VM.

### Demo Databases (Demo Mode Only)
SQLite demo databases are generated in `/tmp/vet_dbs/` on first startup. These are temporary and regenerated if deleted.

### Production Databases
In production mode, the app connects to the real database on the VM. No data is copied or stored locally - the app only reads query results into memory for display and comparison.

## Installation Steps

### 0. Create Azure VM (if not already provisioned)

```bash
# Using Azure CLI
az vm create \
  --resource-group rg-vet-practices \
  --name vet-sql-tester \
  --image UbuntuLTS \
  --size Standard_B1s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --os-disk-size-gb 30

# Open SSH port (app itself runs on localhost, no public HTTP needed)
az vm open-port --resource-group rg-vet-practices \
  --name vet-sql-tester --port 22 --priority 1000

# Get the VM's public IP
az vm show --resource-group rg-vet-practices \
  --name vet-sql-tester -d --query publicIps -o tsv

# SSH into the VM
ssh azureuser@<vm-ip>
```

### 1. Install Python (on the Azure VM)

```bash
# Ubuntu 22.04 LTS from Azure Marketplace has Python 3 pre-installed
# Just ensure pip is available:
sudo apt update
sudo apt install python3-pip -y
```

### 2. Create Install Directory

```bash
sudo mkdir -p /opt/vet-sql-tester
sudo chown $(whoami) /opt/vet-sql-tester
```

### 3. Copy App Files

Copy all files from this project into the install directory:
```bash
cp app.py app.yaml requirements.txt data_generator.py /opt/vet-sql-tester/
mkdir -p /opt/vet-sql-tester/templates
cp templates/index.html /opt/vet-sql-tester/templates/
```

### 4. Create Baseline Storage Directory

```bash
mkdir -p /opt/vet-sql-tester/baselines
```

This is where baseline snapshots will be saved. Choose a location on a persistent drive if you want baselines to survive VM reboots.

### 5. Install Dependencies

```bash
cd /opt/vet-sql-tester
pip3 install -r requirements.txt

# For production mode, also install the database driver:
# SQL Server:
pip3 install pyodbc
# PostgreSQL:
pip3 install psycopg2-binary
# MySQL:
pip3 install pymysql
```

### 6. Configure Baseline Storage Location (Optional)

```bash
# Default is /opt/vet-sql-tester/baselines
# Override to use a different drive or mounted volume:
export VET_BASELINE_DIR=/mnt/data/vet-baselines
```

### 7. Run the App

```bash
cd /opt/vet-sql-tester
python3 app.py
```

The app starts on port 8000 by default. Open `http://localhost:8000` in a browser on the VM.

### 8. Run as a Service (Recommended)

Create a systemd service so the app starts automatically:

```bash
sudo tee /etc/systemd/system/vet-sql-tester.service > /dev/null << 'EOF'
[Unit]
Description=Vet Practice SQL Tester
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/vet-sql-tester
Environment=VET_BASELINE_DIR=/opt/vet-sql-tester/baselines
ExecStart=/usr/bin/python3 /opt/vet-sql-tester/app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable vet-sql-tester
sudo systemctl start vet-sql-tester
```

Check status:
```bash
sudo systemctl status vet-sql-tester
```

### 9. Configure for Production (Connect to Real Database)

Edit `app.py` and modify the `run_query_on_db()` function to connect to the real database on the VM instead of SQLite:

```python
# Example for SQL Server:
import pyodbc

def run_query_on_db(practice, query):
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost;'
        'DATABASE=vet_practice;'
        'Trusted_Connection=yes;'
        'ApplicationIntent=ReadOnly;'  # Read-only connection
    )
    cursor = conn.cursor()
    cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    # ... return results in same format
```

Key points for production:
- Use `ApplicationIntent=ReadOnly` (SQL Server) or equivalent read-only mode
- Keep the keyword validation in `validate_query()` as defense in depth
- Data never leaves the VM - the app connects to localhost only

## Usage Workflow

### Before-After Deploy Comparison

1. **Before deploy:** Run your verification query (e.g., `* FROM patients WHERE healthcare_plan IS NOT NULL`)
2. Click **Save Baseline** and name it (e.g., `pre_healthcare_update`)
3. **Apply your database update** (e.g., update healthcare plans in 3 of 10 databases)
4. **After deploy:** Run the same query
5. Select the baseline from the **Load Baseline** dropdown
6. Click **Compare**
7. Review results:
   - Databases that changed show "N rows with data changes" with old value to new value
   - Databases you missed show "IDENTICAL" (you forgot to update them!)
   - Summary shows total databases with changes vs identical

### Disk Space Management

Baselines accumulate over time. To clean up old baselines:
```bash
# List all baselines
ls -lh /opt/vet-sql-tester/baselines/

# Delete baselines older than 30 days
find /opt/vet-sql-tester/baselines/ -name '*.json' -mtime +30 -delete
```

## Security Notes

- The app runs on localhost only - no external network access required
- SELECT is hardcoded - users cannot run INSERT, UPDATE, DELETE, or DDL
- Databases open in read-only mode (defense in depth)
- No data leaves the VM - no cloud upload, no AI services, no external API calls
- Baselines are stored as plain JSON files on the VM's local disk
- No authentication built in - rely on VM access controls (SSH, firewall) to restrict who can reach the web app