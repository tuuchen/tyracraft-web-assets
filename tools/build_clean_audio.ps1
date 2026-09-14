$ErrorActionPreference = 'Stop'

$taskRoot = (Resolve-Path $PSScriptRoot).Path
$cleanRoot = (Resolve-Path (Join-Path $taskRoot 'clean-assets')).Path
$soundRoot = Join-Path $cleanRoot 'sounds'
$pcmRoot = Join-Path $taskRoot 'generated-clean-audio'

if (-not $cleanRoot.StartsWith($taskRoot, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'Clean asset directory escaped the task workspace.'
}
if (Test-Path -LiteralPath $pcmRoot) {
  $resolvedPcm = (Resolve-Path -LiteralPath $pcmRoot).Path
  if (-not $resolvedPcm.StartsWith($taskRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Generated audio directory escaped the task workspace.'
  }
  Remove-Item -LiteralPath $resolvedPcm -Recurse -Force
}
New-Item -ItemType Directory -Path $pcmRoot | Out-Null

# Keep only the two music tracks with explicit redistribution records.
$allowedMusic = @('silent-wood.wav', 'coverless-book-lofi-186307.wav')
Get-ChildItem -LiteralPath $soundRoot -Recurse -File -Filter '*.wav' |
  Where-Object { $_.Name -notin $allowedMusic } |
  Remove-Item -Force

# Replace every release ADPCM effect whose provenance was not documented.
Get-ChildItem -LiteralPath $soundRoot -Recurse -File -Filter '*.adpcm' |
  Remove-Item -Force

$effects = @(
  'dig/grass1', 'dig/gravel1', 'dig/sand1', 'dig/snow1', 'dig/stone1', 'dig/wood1',
  'step/grass1', 'step/gravel1', 'step/sand1', 'step/snow1', 'step/stone1', 'step/wood1',
  'liquid/splash', 'liquid/splash1', 'liquid/splash2',
  'liquid/swim1', 'liquid/swim2', 'liquid/swim3', 'liquid/swim4', 'liquid/water',
  'mob/pig/death', 'mob/pig/say1', 'mob/pig/say2', 'mob/pig/say3',
  'mob/pig/step1', 'mob/pig/step2', 'mob/pig/step3', 'mob/pig/step4', 'mob/pig/step5',
  'random/click', 'random/glass1', 'random/wood_click'
)

for ($index = 0; $index -lt $effects.Count; $index++) {
  $relative = $effects[$index]
  $wavPath = Join-Path $pcmRoot ($relative + '.wav')
  New-Item -ItemType Directory -Force -Path (Split-Path $wavPath) | Out-Null
  $duration = if ($relative -eq 'liquid/water') { 0.9 } elseif ($relative -like 'mob/pig/*') { 0.32 } else { 0.18 }
  $frequency = 260 + (($index * 73) % 620)
  if ($relative -like 'mob/pig/*') {
    $source = "sine=frequency=${frequency}:duration=${duration}:sample_rate=22050"
    $filter = 'volume=0.16,afade=t=out:st=0.20:d=0.12'
  } elseif ($relative -like 'liquid/*') {
    $source = "anoisesrc=color=pink:duration=${duration}:sample_rate=22050"
    $filter = "lowpass=f=$($frequency + 500),volume=0.11,afade=t=out:st=$([Math]::Max(0.05, $duration - 0.1)):d=0.1"
  } else {
    $source = "anoisesrc=color=white:duration=${duration}:sample_rate=22050"
    $filter = "lowpass=f=$($frequency + 700),volume=0.09,afade=t=out:st=0.08:d=0.1"
  }
  & ffmpeg -hide_banner -loglevel error -y -f lavfi -i $source -af $filter -ac 1 -ar 22050 -c:a pcm_s16le $wavPath
}

# Original, synthetic menu ambience and MazeCraft completion cue.
$menuPath = Join-Path $soundRoot 'menu/portal-ambient.wav'
& ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'aevalsrc=0.055*sin(2*PI*110*t)+0.035*sin(2*PI*165*t)+0.025*sin(2*PI*220*t):d=45:s=22050' -af 'afade=t=in:d=2,afade=t=out:st=42:d=3' -ac 1 -ar 22050 -c:a pcm_s16le $menuPath
$clearPath = Join-Path $soundRoot 'game/mazecraft/portal-level-done.wav'
& ffmpeg -hide_banner -loglevel error -y -f lavfi -i 'sine=frequency=660:duration=1.2:sample_rate=22050' -af 'volume=0.12,afade=t=out:st=0.7:d=0.5' -ac 1 -ar 22050 -c:a pcm_s16le $clearPath

$pcmDocker = $pcmRoot.Replace('\', '/')
$soundDocker = $soundRoot.Replace('\', '/')
$convert = 'find /input -type f -name ''*.wav'' -print0 | while IFS= read -r -d '''' f; do rel=${f#/input/}; out=/output/${rel%.wav}.adpcm; mkdir -p "$(dirname "$out")"; ps2adpcm "$f" "$out"; done'
& docker run --rm -v "${pcmDocker}:/input" -v "${soundDocker}:/output" h4570/tyra bash -lc $convert
if ($LASTEXITCODE -ne 0) { throw 'PS2 ADPCM conversion failed.' }

Add-Content -LiteralPath (Join-Path $cleanRoot 'ASSET-NOTICES.md') -Value @'

All undocumented release ADPCM effects and undocumented music files were removed.
Replacement effects, menu ambience, and the MazeCraft completion cue were synthesized
for this portal build and encoded with PS2SDK's `ps2adpcm` tool.
'@

Write-Output "clean audio staged at $soundRoot"
