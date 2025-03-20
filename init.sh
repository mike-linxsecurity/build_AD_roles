#!/bin/bash

# Exit on error
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks if git is initialized
if [ -d ".git" ]; then
    # Install pre-commit hooks
    pre-commit install
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOL
# Environment Configuration
LOG_LEVEL=INFO
EXCEL_MAX_ROWS=1000000
EXCEL_MAX_COLS=16384
EOL
fi

# Create builtin_groups.json if it doesn't exist
if [ ! -f "src/builtin_groups.json" ]; then
    echo "Creating builtin_groups.json..."
    mkdir -p src
    cat > src/builtin_groups.json << EOL
{
    "BuiltIn_AD_Groups": [
        "Domain Admins",
        "Enterprise Admins",
        "Schema Admins",
        "Pre-Windows 2000 Compatible Access",
        "Cert Publishers",
        "RAS and IAS Servers",
        "Windows Authorization Access Group",
        "DnsAdmins"
    ],
    "Original_Role_Groups": [
        "RDS Remote Access Servers",
        "RDS Endpoint Servers",
        "RDS Management Servers",
        "Hyper-V Administrators",
        "Access Control Assistance Operators",
        "Remote Management Users",
        "Performance Monitor Users",
        "Backup Operators",
        "Account Operators",
        "Server Operators",
        "Administrators",
        "Certificate Service DCOM Access",
        "Remote Desktop Users",
        "Event Log Readers",
        "Print Operators",
        "Group Policy Creator Owners",
        "Network Configuration Operators",
        "Distributed COM Users",
        "Cryptographic Operators",
        "Performance Log Users"
    ],
    "Exchange_Server_Groups": [
        "Exchange Organization Management",
        "Exchange Recipient Management",
        "Exchange Server Management",
        "Exchange Trusted Subsystem",
        "Discovery Management",
        "Exchange Windows Permissions",
        "ExchangeLegacyInterop"
    ],
    "SharePoint_Groups": [
        "WSS_WPG",
        "WSS_ADMIN_WPG",
        "SharePoint_Shell_Access"
    ],
    "Azure_AD_Entra_ID_Groups": [
        "Global Administrator",
        "Exchange Online Organization Management",
        "Exchange Online Recipient Management",
        "Intune Administrator",
        "Security Administrator",
        "Compliance Administrator",
        "Privileged Role Administrator"
    ],
    "Additional_Enterprise_Groups": [
        "TS Web Access Administrators",
        "Remote Access Servers",
        "WinRMRemoteWMIUsers__",
        "Storage Replica Administrators",
        "Key Admins",
        "Enterprise Key Admins"
    ]
}
EOL
fi

# Make init.sh executable
chmod +x init.sh

echo "Initialization complete! Virtual environment is active and dependencies are installed."

