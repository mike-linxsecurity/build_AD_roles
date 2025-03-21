# AD_Export.ps1
# Maintained by the Linx Security team
# Version: 1.1 - 2025-03-12
#
# PURPOSE:
# This script exports Active Directory (AD) data including users, groups, roles, and their relationships
# to an Excel file for further processing and analysis.
#
# FEATURES:
# - Exports Users with detailed attributes
# - Exports Groups and nested group relationships
# - Maps built-in AD roles and permissions
# - Handles Azure AD/Entra ID integration
# - Includes error handling and retry logic
# - Performance optimized for large directories
#
# PREREQUISITES:
# - PowerShell 5.1 or higher
# - ImportExcel module
# - Active Directory module
# - Appropriate AD read permissions
#
# OUTPUT:
# Creates an Excel file with the following sheets:
# - Users: User details and attributes
# - Groups: AD group information
# - Roles: Mapped AD roles
# - User_Groups: User-to-group memberships
# - Group_Groups: Nested group relationships
# - Role_Groups: Role-to-group mappings

# Detect PowerShell version
$PowerShellVersion = $PSVersionTable.PSVersion.Major
Write-Host "Running on PowerShell version: $PowerShellVersion"

# Check if ImportExcel module exists and install it if missing
if (!(Get-Module -ListAvailable -Name ImportExcel)) {
    Write-Host "ImportExcel module not found. Attempting to install..."
    Install-Module -Name ImportExcel -Scope CurrentUser -Force
}

# Start overall timer
$scriptStartTime = Get-Date
Write-Host "Script started at: $( $scriptStartTime.ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') ) UTC"

# Import required modules
try {
    Import-Module ImportExcel -ErrorAction Stop
    Import-Module ActiveDirectory -ErrorAction Stop
    Write-Host "Modules imported successfully."
} catch {
    Write-Error "Required module missing: $($_.Exception.Message)"
    exit 1
}

# Create output directory if it doesn't exist
$outputPath = "C:\Temp"
if (-not (Test-Path -Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force
    Write-Host "Created output directory: $outputPath"
}

# Set timestamp and output file name with full path
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd_HHmm")
$outputFile = Join-Path -Path $outputPath -ChildPath "AD_Export_$timestamp.xlsx"
Write-Host "Output file will be: $outputFile"

# Get the current domain of the operator and restrict queries to this domain only
try {
    $currentDomain = [System.DirectoryServices.ActiveDirectory.Domain]::GetCurrentDomain()
    $domainName = $currentDomain.Name
    Write-Host "Targeting domain: $domainName"
} catch {
    Write-Error "Unable to retrieve the current domain: $_"
    exit 1
}

# Define built-in groups directly in the script
$builtinGroups = @{
    BuiltIn_AD_Groups = @(
        "Domain Admins",
        "Enterprise Admins",
        "Schema Admins",
        "Pre-Windows 2000 Compatible Access",
        "Cert Publishers",
        "RAS and IAS Servers",
        "Windows Authorization Access Group",
        "DnsAdmins"
    )
    Original_Role_Groups = @(
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
    )
    Exchange_Server_Groups = @(
        "Exchange Organization Management",
        "Exchange Recipient Management",
        "Exchange Server Management",
        "Exchange Trusted Subsystem",
        "Discovery Management",
        "Exchange Windows Permissions",
        "ExchangeLegacyInterop"
    )
    SharePoint_Groups = @(
        "WSS_WPG",
        "WSS_ADMIN_WPG",
        "SharePoint_Shell_Access"
    )
    Azure_AD_Entra_ID_Groups = @(
        "Global Administrator",
        "Exchange Online Organization Management",
        "Exchange Online Recipient Management",
        "Intune Administrator",
        "Security Administrator",
        "Compliance Administrator",
        "Privileged Role Administrator"
    )
    Additional_Enterprise_Groups = @(
        "TS Web Access Administrators",
        "Remote Access Servers",
        "WinRMRemoteWMIUsers__",
        "Storage Replica Administrators",
        "Key Admins",
        "Enterprise Key Admins"
    )
}

# Retry logic for AD operations
$maxRetries = 3
$retryDelay = 5  # seconds

# Retrieve AD Users with MemberOf property
$usersStartTime = Get-Date
$rawUsers = $null
$retryCount = 0
do {
    try {
        $rawUsers = Get-ADUser -Filter * `
            -Server $domainName `
            -Properties ObjectGUID, DistinguishedName, GivenName, Surname, DisplayName, SamAccountName, Mail, Enabled, WhenCreated, WhenChanged, LastLogonDate, 'msDS-ExternalDirectoryObjectId', Company, Department, Title, Manager, MemberOf `
            -ErrorAction Stop
        break
    } catch {
        $retryCount++
        if ($retryCount -ge $maxRetries) {
            Write-Error "Error retrieving AD users after $maxRetries attempts: $_"
            exit 1
        }
        Write-Warning "Attempt $retryCount failed: $_"
        Start-Sleep -Seconds $retryDelay
    }
} while ($true)

# Build DN-to-ID hashtable for manager lookups
$userDnToId = @{}
foreach ($user in $rawUsers) {
    $userDnToId[$user.DistinguishedName] = $user.ObjectGUID.ToString()
}

# Process users into a formatted list
$users = $rawUsers | Select-Object `
    @{Name="user_id"; Expression={ $_.ObjectGUID.ToString() }},
    @{Name="first_name"; Expression={ $_.GivenName }},
    @{Name="last_name"; Expression={ $_.Surname }},
    @{Name="full_name"; Expression={ $_.DisplayName }},
    @{Name="username"; Expression={ $_.SamAccountName }},
    @{Name="email"; Expression={ $_.Mail }},
    @{Name="is_active"; Expression={ if ($_.Enabled) { "yes" } else { "no" } }},
    @{Name="created_at"; Expression={ if ($_.WhenCreated) { $_.WhenCreated.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss") } else { "" } }},
    @{Name="updated_at"; Expression={ if ($_.WhenChanged) { $_.WhenChanged.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss") } else { "" } }},
    @{Name="last_login_at"; Expression={ if ($_.LastLogonDate) { $_.LastLogonDate.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } else { "" } }},
    @{Name="object_id"; Expression={ if ($_.'msDS-ExternalDirectoryObjectId') { $_.'msDS-ExternalDirectoryObjectId' } else { "" } }},
    @{Name="user_type"; Expression={ if ($_.'msDS-ExternalDirectoryObjectId') { "Guest" } else { "Member" } }},
    @{Name="company_name"; Expression={ $_.Company }},
    @{Name="department"; Expression={ $_.Department }},
    @{Name="job_title"; Expression={ $_.Title }},
    @{Name="manager_id"; Expression={ if ($_.Manager -and $userDnToId.ContainsKey($_.Manager)) { $userDnToId[$_.Manager] } else { "" } }}
Write-Host "Retrieved $($users.Count) users."

$usersEndTime = Get-Date
$usersDuration = ($usersEndTime - $usersStartTime).TotalSeconds
Write-Host "Time to retrieve and process users: $([math]::Round($usersDuration / 60, 2)) minutes ($([math]::Round($usersDuration, 2)) seconds)"

# Retrieve AD Groups without Members property
$groupsStartTime = Get-Date
$groups = $null
$retryCount = 0
do {
    try {
        $groups = Get-ADGroup -Filter * `
            -Server $domainName `
            -Properties ObjectGUID, Name, Description, MemberOf, DistinguishedName `
            -ErrorAction Stop |
            Select-Object `
                @{Name="group_id"; Expression={ $_.ObjectGUID.ToString() }},
                @{Name="group_name"; Expression={ $_.Name }},
                @{Name="group_description"; Expression={ $_.Description }},
                @{Name="MemberOf"; Expression={ $_.MemberOf }},
                @{Name="DistinguishedName"; Expression={ $_.DistinguishedName }}
        break
    } catch {
        $retryCount++
        if ($retryCount -ge $maxRetries) {
            Write-Error "Error retrieving AD groups after $maxRetries attempts: $_"
            exit 1
        }
        Write-Warning "Attempt $retryCount failed: $_"
        Start-Sleep -Seconds $retryDelay
    }
} while ($true)
Write-Host "Retrieved $($groups.Count) groups."

# Build DN-to-ID hashtable for groups
$groupDnToId = @{}
foreach ($group in $groups) {
    $groupDnToId[$group.DistinguishedName] = $group.group_id
}

# Process group-group relationships
$groupGroups = New-Object System.Collections.Generic.List[PSCustomObject]
foreach ($group in $groups) {
    if ($group.MemberOf -and $group.MemberOf.Count -gt 0) {
        foreach ($parentGroupDn in $group.MemberOf) {
            if ($parentGroupDn -and $groupDnToId.ContainsKey($parentGroupDn)) {
                $groupGroups.Add([PSCustomObject]@{
                    source_group_id = $group.group_id
                    destination_group_id = $groupDnToId[$parentGroupDn]
                })
            }
        }
    }
}
Write-Host "Found $($groupGroups.Count) group-group relationships."

# Process roles and role-groups based on builtin groups
$roles = New-Object System.Collections.Generic.List[PSCustomObject]
$roleGroups = New-Object System.Collections.Generic.List[PSCustomObject]

# Combine all role-eligible groups
$roleEligibleGroups = @()
$roleEligibleGroups += $builtinGroups.Original_Role_Groups
$roleEligibleGroups += $builtinGroups.Exchange_Server_Groups
$roleEligibleGroups += $builtinGroups.SharePoint_Groups
$roleEligibleGroups += $builtinGroups.Azure_AD_Entra_ID_Groups
$roleEligibleGroups += $builtinGroups.Additional_Enterprise_Groups

# Create roles and role-groups mappings
foreach ($group in $groups) {
    if ($roleEligibleGroups -contains $group.group_name) {
        # Add to roles
        $roles.Add([PSCustomObject]@{
            role_id = $group.group_id
            role_name = $group.group_name
            description = $group.group_description
        })

        # Add to role-groups
        $roleGroups.Add([PSCustomObject]@{
            group_id = $group.group_id
            role_id = $group.group_id
        })
    }
}

Write-Host "Found $($roles.Count) roles and $($roleGroups.Count) role-group mappings."

$groupsEndTime = Get-Date
$groupsDuration = ($groupsEndTime - $groupsStartTime).TotalSeconds
Write-Host "Time to retrieve and process groups: $([math]::Round($groupsDuration / 60, 2)) minutes ($([math]::Round($groupsDuration, 2)) seconds)"

# Process user-group relationships
$userGroupsStartTime = Get-Date
$userGroups = New-Object System.Collections.Generic.List[PSCustomObject]

Write-Host "Processing user-group memberships..."
foreach ($user in $rawUsers) {
    if ($user.MemberOf -and $user.MemberOf.Count -gt 0) {
        foreach ($groupDn in $user.MemberOf) {
            if ($groupDn -and $groupDnToId.ContainsKey($groupDn)) {
                $userGroups.Add([PSCustomObject]@{
                    user_id = $user.ObjectGUID.ToString()
                    group_id = $groupDnToId[$groupDn]
                })
            }
        }
    }
}

$userGroupsEndTime = Get-Date
$userGroupsDuration = ($userGroupsEndTime - $userGroupsStartTime).TotalSeconds
Write-Host "Found $($userGroups.Count) user-group relationships."
Write-Host "Time to process user-group relationships: $([math]::Round($userGroupsDuration, 2)) seconds"

# Export data to Excel
try {
    Write-Host "Exporting data to: $outputFile"
    # Export sheets in specified order: Users, Groups, Roles, User_Groups, Group_Groups, Role_Groups
    $users | Export-Excel -Path $outputFile -WorksheetName "Users" -AutoSize -ClearSheet
    $groups | Export-Excel -Path $outputFile -WorksheetName "Groups" -AutoSize -ClearSheet
    $roles | Export-Excel -Path $outputFile -WorksheetName "Roles" -AutoSize -ClearSheet
    $userGroups | Export-Excel -Path $outputFile -WorksheetName "User_Groups" -AutoSize -ClearSheet
    $groupGroups | Export-Excel -Path $outputFile -WorksheetName "Group_Groups" -AutoSize -ClearSheet
    $roleGroups | Export-Excel -Path $outputFile -WorksheetName "Role_Groups" -AutoSize -ClearSheet
    Write-Host "Data exported successfully to: $outputFile"
} catch {
    Write-Error "Error during Excel export: $_"
    Write-Host "Attempted to write to: $outputFile"
    exit 1
}

# Add summary report generation before script end
$scriptEndTime = Get-Date
$totalDuration = ($scriptEndTime - $scriptStartTime).TotalSeconds

# Create and display summary report
Write-Host @"

========================================
   AD Export Summary Report
========================================
Run Date (UTC): $($scriptStartTime.ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss'))
Domain: $domainName
Output File: $outputFile

Data Collection Statistics:
-------------------------
Users Found: $($users.Count)
Groups Found: $($groups.Count)
Roles Mapped: $($roles.Count)
User-Group Relations: $($userGroups.Count)
Group-Group Relations: $($groupGroups.Count)
Role-Group Mappings: $($roleGroups.Count)

Performance Metrics:
------------------
Users Processing Time: $([math]::Round($usersDuration / 60, 2)) minutes
Groups Processing Time: $([math]::Round($groupsDuration / 60, 2)) minutes
User-Groups Processing Time: $([math]::Round($userGroupsDuration, 2)) seconds
Total Execution Time: $([math]::Round($totalDuration / 60, 2)) minutes

Status: Export Completed Successfully
========================================

"@
