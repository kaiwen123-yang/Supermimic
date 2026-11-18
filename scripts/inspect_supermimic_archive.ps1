# Read-only Windows inventory. Does not create, copy, move, or delete anything.
# Run in the user's local Windows PowerShell, not in the ChatGPT Linux container.
[CmdletBinding()]
param(
    [Parameter()]
    [ValidatePattern('^[A-Za-z]:\\')]
    [string]$ArchiveRoot = 'H:\Supermimic'
)

$ErrorActionPreference = 'Stop'
$archiveItem = Get-Item -LiteralPath $ArchiveRoot -Force
if (-not $archiveItem.PSIsContainer) {
    throw 'ArchiveRoot must be an existing directory.'
}
if ($archiveItem.PSProvider.Name -ne 'FileSystem') {
    throw 'ArchiveRoot must use the FileSystem provider.'
}
if (($archiveItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'ArchiveRoot is a reparse point. Resolve its real destination and volume before continuing.'
}

function Get-ArchiveEntryMetadata {
    param([System.IO.FileSystemInfo]$ArchiveEntry)
    $entryBytes = $null
    if (-not $ArchiveEntry.PSIsContainer) { $entryBytes = $ArchiveEntry.Length }
    [pscustomobject]@{
        name = $ArchiveEntry.Name
        path = $ArchiveEntry.FullName
        is_directory = [bool]$ArchiveEntry.PSIsContainer
        bytes = $entryBytes
        last_write_time_utc = $ArchiveEntry.LastWriteTimeUtc.ToString('o')
        attributes = $ArchiveEntry.Attributes.ToString()
    }
}

$archiveDriveId = $archiveItem.PSDrive.Name + ':'
$archiveVolume = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='$archiveDriveId'"
if ($null -eq $archiveVolume) {
    throw 'Cannot identify the actual Windows volume. Do not create a substitute archive root.'
}

$archiveTopEntries = @(Get-ChildItem -LiteralPath $archiveItem.FullName -Force | Sort-Object Name)
$archiveDirectoryDetails = @(
    foreach ($archiveDirectory in $archiveTopEntries) {
        if (-not $archiveDirectory.PSIsContainer) { continue }
        # Do not follow top-level junctions/symlinks into unrelated locations.
        if (($archiveDirectory.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
            [pscustomobject]@{
                directory = $archiveDirectory.FullName
                skipped_reparse_point = $true
                child_count = $null
                shown_count = 0
                truncated = $false
                entries = @()
            }
            continue
        }
        $archiveChildren = @(Get-ChildItem -LiteralPath $archiveDirectory.FullName -Force | Sort-Object Name)
        $archiveShown = @($archiveChildren | Select-Object -First 200)
        [pscustomobject]@{
            directory = $archiveDirectory.FullName
            skipped_reparse_point = $false
            child_count = $archiveChildren.Count
            shown_count = $archiveShown.Count
            truncated = ($archiveChildren.Count -gt $archiveShown.Count)
            entries = @($archiveShown | ForEach-Object { Get-ArchiveEntryMetadata -ArchiveEntry $_ })
        }
    }
)

[pscustomobject]@{
    operation = 'read_only_archive_layout_inventory'
    observed_at_utc = [DateTime]::UtcNow.ToString('o')
    archive_root = $archiveItem.FullName
    root_attributes = $archiveItem.Attributes.ToString()
    volume = [pscustomobject]@{
        device_id = $archiveVolume.DeviceID
        drive_type = $archiveVolume.DriveType
        file_system = $archiveVolume.FileSystem
        volume_name = $archiveVolume.VolumeName
        total_bytes = $archiveVolume.Size
        free_bytes = $archiveVolume.FreeSpace
    }
    top_level = @($archiveTopEntries | ForEach-Object { Get-ArchiveEntryMetadata -ArchiveEntry $_ })
    directory_children = $archiveDirectoryDetails
    archive_payloads_read = $false
    files_created = 0
    files_deleted = 0
    note = 'Metadata only. Read the existing receipts, fully decode local payloads, and confirm their data integrity or compare with source content before source deletion. Truncated listings require explicit follow-up.'
} | ConvertTo-Json -Depth 8
