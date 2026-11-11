param(
    [string]$ArchiveRoot = 'H:\Supermimic'
)

$Categories = @(
    '00_inventory',
    '01_source_datasets\BONES',
    '01_source_datasets\LAFAN1',
    '02_processed_data\active_copy_only',
    '02_processed_data\retired',
    '03_checkpoints\anchors_copy_only',
    '03_checkpoints\historical',
    '04_trajectories',
    '05_logs',
    '06_videos',
    '07_results_and_configs',
    '98_incoming'
)

New-Item -ItemType Directory -Path $ArchiveRoot -Force -ErrorAction Stop | Out-Null
foreach ($Category in $Categories) {
    New-Item -ItemType Directory -Path (Join-Path $ArchiveRoot $Category) -Force -ErrorAction Stop | Out-Null
}

Get-ChildItem -LiteralPath $ArchiveRoot -Directory | Select-Object Name, FullName
