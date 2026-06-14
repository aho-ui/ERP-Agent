if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell "-ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$python  = "C:\Program Files\Odoo 18.0.20260415\python\python.exe"
$odooBin = "C:\Program Files\Odoo 18.0.20260415\server\odoo-bin"
$odooCfg = "C:\Program Files\Odoo 18.0.20260415\server\odoo.conf"
$service = "odoo-server-18.0"
$db      = "odoo_dev_18"

Write-Host "Stopping $service..."
Stop-Service -Name $service -ErrorAction Stop

Write-Host "Running CLI upgrade of erp_agent on $db..."
& $python $odooBin -c $odooCfg -d $db -u erp_agent --stop-after-init
$exit = $LASTEXITCODE

if ($exit -ne 0) {
    Write-Host "Upgrade exited with code $exit. Service not restarted. Inspect odoo.log." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit $exit
}

Write-Host "Starting $service..."
Start-Service -Name $service -ErrorAction Stop

Write-Host "Done"
Read-Host "Press Enter to exit"
