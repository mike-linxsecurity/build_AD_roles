#!/bin/bash

# Exit on error
set -e

# Function to detect shell type
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$BASH_VERSION" ]; then
        echo "bash"
    else
        echo "unknown"
    fi
}

# Function to activate virtual environment based on shell
activate_venv() {
    local shell_type=$(detect_shell)
    case $shell_type in
        "zsh"|"bash")
            source venv/bin/activate
            ;;
        *)
            echo "Unsupported shell type: $shell_type"
            exit 1
            ;;
    esac
}

# Function to print usage
print_usage() {
    echo "Usage:
    ./init.sh              # Initialize environment
    ./init.sh -t          # Initialize with test dependencies and run tests
    ./init.sh --convert   # Convert AD data from input directory
    ./init.sh -h          # Show this help message"
    exit 1
}

# Parse command line arguments
TEST_MODE=false
CONVERT_MODE=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        --convert)
            CONVERT_MODE=true
            shift
            ;;
        -h|--help)
            print_usage
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            ;;
    esac
done

# Function to check if we're in the correct directory
check_directory() {
    if [ ! -f "init.sh" ]; then
        # We're not in the project directory, need to clone
        if [ ! -d "build_AD_roles" ]; then
            echo "Cloning repository..."
            git clone https://github.com/[username]/build_AD_roles.git
        fi
        cd build_AD_roles || exit 1
    fi
}

# Check and setup directory
check_directory

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
activate_venv

# Create necessary directories
mkdir -p src input output logs

# Upgrade pip silently
python -m pip install -q --upgrade pip >/dev/null 2>&1

# Install dependencies
if [ "$TEST_MODE" = true ]; then
    echo "Installing test dependencies..."
    python -m pip install -q -r requirements.txt >/dev/null 2>&1
    python -m pip install -q pytest pytest-cov pre-commit >/dev/null 2>&1
else
    echo "Installing dependencies..."
    python -m pip install -q -r requirements.txt >/dev/null 2>&1
fi

# Set up pre-commit hooks if git is initialized and in test mode
if [ "$TEST_MODE" = true ] && [ -d ".git" ]; then
    echo "Setting up pre-commit hooks..."
    pre-commit install >/dev/null 2>&1
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

# Create activation script for PowerShell
cat > activate.ps1 << EOL
# PowerShell activation script
if (Test-Path "venv/Scripts/Activate.ps1") {
    . venv/Scripts/Activate.ps1
} elseif (Test-Path "venv/bin/Activate.ps1") {
    . venv/bin/Activate.ps1
} else {
    Write-Error "Virtual environment activation script not found"
    exit 1
}
EOL

if [ "$TEST_MODE" = true ]; then
    echo "Initialization complete! Test environment is ready with pre-commit hooks and test dependencies."
else
    echo "Initialization complete! Regular environment is ready for use."
fi

# Print activation instructions based on shell
SHELL_TYPE=$(detect_shell)
case "$SHELL_TYPE" in
    "bash"|"zsh")
        echo "To activate the virtual environment, run:"
        echo "  source venv/bin/activate"
        ;;
    *)
        echo "To activate the virtual environment, run:"
        echo "  . venv/bin/activate    # For bash/zsh"
        echo "  . venv/Scripts/activate    # For Windows CMD"
        echo "  . ./activate.ps1    # For PowerShell"
        ;;
esac

# Run tests if in test mode
if [ "$TEST_MODE" = true ]; then
    echo "Running tests..."
    python -m pytest tests/ -v
fi

# Run conversion if in convert mode
if [ "$CONVERT_MODE" = true ]; then
    echo "Running AD data conversion..."
    if [ ! -d "input" ] || [ -z "$(ls -A input/*.xlsx 2>/dev/null)" ]; then
        echo "❌ No Excel files found in input directory."
        echo "Please place your AD export files in the 'input' directory."
        exit 1
    fi
    python convert_ad_data.py
    if [ $? -eq 0 ]; then
        echo "✅ Conversion completed successfully!"
        echo "Check the 'output' directory for processed files."
    fi
    exit 0
fi

# Print usage information if no mode specified
if [ "$TEST_MODE" = false ] && [ "$CONVERT_MODE" = false ]; then
    print_usage
fi
