# usage (Windows): powershell -ExecutionPolicy Bypass -File scripts/fpga/xc7z020/device_view.ps1 <dir> [vivado.bat]
# Upstream's btle_controller_xilinx_7z020.jpg is Vivado's Device view, which batch mode cannot export. This
# opens <dir>/routed.dcp in the GUI (device_view.tcl highlights btle_tx), maximizes the window and its Device
# panel, captures the window to <dir>/device_full.png and closes the Vivado it started; then device_crop.py.
# The screen must be unlocked and left alone for a minute: the Vivado window comes to the front, the mouse
# clicks the Device panel's maximize button and Zoom Fit, and goes back where it was after the capture.
param([Parameter(Mandatory = $true)][string]$Dir, [string]$Vivado = "C:\AMDDesignTools\2026.1\Vivado\bin\vivado.bat")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class DeviceViewWin {
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  public struct RECT { public int L, T, R, B; }
  public struct POINT { public int X, Y; }
  public static void Click(int x, int y) {
    SetCursorPos(x, y); System.Threading.Thread.Sleep(200);
    mouse_event(2, 0, 0, 0, IntPtr.Zero); mouse_event(4, 0, 0, 0, IntPtr.Zero);
  }
}
"@
[DeviceViewWin]::SetProcessDPIAware() | Out-Null
$Dir = (Resolve-Path $Dir).Path
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ready = Join-Path $Dir "device.txt"
Remove-Item $ready -ErrorAction SilentlyContinue
$cmd = Start-Process -FilePath $Vivado -WorkingDirectory $Dir -PassThru -WindowStyle Minimized `
  -ArgumentList "-mode gui -nojournal -nolog -source $(($here -replace '\\', '/') + '/device_view.tcl') -tclargs $($Dir -replace '\\', '/')"

function Grab($h) {
  $r = New-Object DeviceViewWin+RECT
  [DeviceViewWin]::GetWindowRect($h, [ref]$r) | Out-Null
  $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
  $g.Dispose()
  return @($bmp, $r)
}

try {
  $t0 = Get-Date
  while (-not (Test-Path $ready)) {
    if (((Get-Date) - $t0).TotalSeconds -gt 600) { throw "timeout: no $ready" }
    Start-Sleep -Milliseconds 500
  }
  # the GUI is vivado.exe, child of the cmd.exe that runs vivado.bat
  $p = $null
  for ($i = 0; $i -lt 60 -and -not $p; $i++) {
    $kid = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($cmd.Id) AND Name='vivado.exe'" | Select-Object -First 1
    if ($kid) { $p = Get-Process -Id $kid.ProcessId | Where-Object { $_.MainWindowTitle -like '*routed.dcp* - Vivado*' } }
    if (-not $p) { Start-Sleep -Milliseconds 500 }
  }
  if (-not $p) { throw "no Vivado window" }
  $h = $p.MainWindowHandle
  $mouse = New-Object DeviceViewWin+POINT
  [DeviceViewWin]::GetCursorPos([ref]$mouse) | Out-Null
  [DeviceViewWin]::ShowWindow($h, 3) | Out-Null   # SW_MAXIMIZE
  [DeviceViewWin]::SetForegroundWindow($h) | Out-Null
  Start-Sleep -Seconds 4
  $s = [DeviceViewWin]::GetDpiForWindow($h) / 96.0
  $bmp, $r = Grab $h
  # in the default layout the Netlist panel (white) sits where the maximized Device canvas (black) would be
  $c = $bmp.GetPixel([int](258 * $s), [int](344 * $s))
  $bmp.Dispose()
  if ($c.R -gt 128) {
    [DeviceViewWin]::Click($r.R - [int](37 * $s), $r.T + [int](161 * $s))   # the Device panel's maximize button
    Start-Sleep -Seconds 4
  }
  [DeviceViewWin]::Click($r.L + [int](186 * $s), $r.T + [int](189 * $s))     # Zoom Fit, in the Device toolbar
  [DeviceViewWin]::SetCursorPos($r.L + [int](($r.R - $r.L) / 2), $r.T + [int](14 * $s)) | Out-Null   # title bar: no tooltip on the canvas
  Start-Sleep -Seconds 3
  $bmp, $r = Grab $h
  [DeviceViewWin]::SetCursorPos($mouse.X, $mouse.Y) | Out-Null
  $bmp.Save((Join-Path $Dir "device_full.png"), [System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose()
  "$Dir\device_full.png: $(Get-Content $ready | Select-Object -Last 1)"
} finally {
  & taskkill /PID $cmd.Id /T /F | Out-Null
}
