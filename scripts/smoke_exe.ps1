# Chạy thử UpScale.exe đã đóng gói: cửa sổ phải sống đủ lâu và app phải ghi được logs\app.log.
# Không cần thư mục engine\: khi thiếu, app hiện màn hình M1 thay vì thoát.
# Dùng: powershell -File scripts\smoke_exe.ps1 [-Dist dist\UpScale] [-Seconds 8]
param(
    [string]$Dist = "dist\UpScale",
    [int]$Seconds = 8
)
$ErrorActionPreference = "Stop"

$exe = Join-Path $Dist "UpScale.exe"
$log = Join-Path $Dist "logs\app.log"
if (-not (Test-Path -LiteralPath $exe)) { throw "Không thấy $exe" }
Remove-Item -LiteralPath $log -ErrorAction SilentlyContinue

$proc = Start-Process -FilePath $exe -WorkingDirectory $Dist -PassThru
try {
    Start-Sleep -Seconds $Seconds
    if ($proc.HasExited) { throw "UpScale.exe thoát sớm với mã $($proc.ExitCode)" }
}
finally {
    if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
}

if (-not (Test-Path -LiteralPath $log)) { throw "App chạy nhưng không ghi $log (kiểm tra PROJECT_ROOT khi đóng gói)" }
Write-Output "OK: UpScale.exe chạy $Seconds giây và đã ghi $log"
