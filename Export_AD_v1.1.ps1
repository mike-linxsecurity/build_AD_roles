 # AD_Export.ps1
# Maintained by the Linx Security team
# Version: 1.1 - 2025-03-12 Performance optimized and error handling improved and collection of Group Groups

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

$groupsEndTime = Get-Date
$groupsDuration = ($groupsEndTime - $groupsStartTime).TotalSeconds
Write-Host "Time to retrieve and process groups: $([math]::Round($groupsDuration / 60, 2)) minutes ($([math]::Round($groupsDuration, 2)) seconds)"

# Export data to Excel
try {
    Write-Host "Exporting data to: $outputFile"
    $users | Export-Excel -Path $outputFile -WorksheetName "Users" -AutoSize -ClearSheet
    $groups | Export-Excel -Path $outputFile -WorksheetName "Groups" -AutoSize -ClearSheet
    $groupGroups | Export-Excel -Path $outputFile -WorksheetName "Group-Group Relationships" -AutoSize -ClearSheet
    Write-Host "Data exported successfully to: $outputFile"
} catch {
    Write-Error "Error during Excel export: $_"
    Write-Host "Attempted to write to: $outputFile"
    exit 1
} 
