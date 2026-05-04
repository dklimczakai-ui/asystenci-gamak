Add-Type -AssemblyName System.Drawing

$w = 1200
$h = 630
$bmp = New-Object System.Drawing.Bitmap $w,$h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'ClearTypeGridFit'
$g.InterpolationMode = 'HighQualityBicubic'

# === Background: dark gradient with red glow ===
$bgRect = New-Object System.Drawing.Rectangle 0,0,$w,$h
$bg = New-Object System.Drawing.Drawing2D.LinearGradientBrush $bgRect, ([System.Drawing.Color]::FromArgb(12,10,9)), ([System.Drawing.Color]::FromArgb(67,10,14)), 135
$g.FillRectangle($bg, $bgRect)
$bg.Dispose()

# === Red glow blob (top-right) ===
$glowPath = New-Object System.Drawing.Drawing2D.GraphicsPath
$glowPath.AddEllipse(700, -200, 700, 700)
$glow = New-Object System.Drawing.Drawing2D.PathGradientBrush $glowPath
$glow.CenterColor = [System.Drawing.Color]::FromArgb(180, 217, 35, 43)
$glow.SurroundColors = @([System.Drawing.Color]::FromArgb(0, 217, 35, 43))
$g.FillEllipse($glow, 700, -200, 700, 700)
$glow.Dispose()
$glowPath.Dispose()

# === Ice glow blob (bottom-left, subtle) ===
$icePath = New-Object System.Drawing.Drawing2D.GraphicsPath
$icePath.AddEllipse(-250, 300, 600, 600)
$iceGlow = New-Object System.Drawing.Drawing2D.PathGradientBrush $icePath
$iceGlow.CenterColor = [System.Drawing.Color]::FromArgb(60, 122, 184, 217)
$iceGlow.SurroundColors = @([System.Drawing.Color]::FromArgb(0, 122, 184, 217))
$g.FillEllipse($iceGlow, -250, 300, 600, 600)
$iceGlow.Dispose()
$icePath.Dispose()

# === Logo (Sport Ice) ===
$logo = [System.Drawing.Image]::FromFile('C:\Users\klimc\Desktop\Asystenci\gamak\marki\sport-ice\website\assets\images\sport-ice-logo.png')
$logoW = 420
$logoH = [int]($logo.Height * $logoW / $logo.Width)
$g.DrawImage($logo, 90, 100, $logoW, $logoH)
$logo.Dispose()

# === Eyebrow ===
$fontEyebrow = New-Object System.Drawing.Font 'Segoe UI', 18, ([System.Drawing.FontStyle]::Bold)
$brushRed = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(246,103,115))
$g.DrawString('WYŁĄCZNY DYSTRYBUTOR W POLSCE', $fontEyebrow, $brushRed, 90, 290)
$brushRed.Dispose()
$fontEyebrow.Dispose()

# === Main headline ===
$fontTitle = New-Object System.Drawing.Font 'Segoe UI', 56, ([System.Drawing.FontStyle]::Bold)
$brushWhite = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$g.DrawString('Maszyny do lodu,', $fontTitle, $brushWhite, 85, 325)
$brushRedTitle = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255,103,115))
$g.DrawString('zaprojektowane jak lód.', $fontTitle, $brushRedTitle, 85, 395)
$brushRedTitle.Dispose()
$brushWhite.Dispose()
$fontTitle.Dispose()

# === Sub ===
$fontSub = New-Object System.Drawing.Font 'Segoe UI', 22, ([System.Drawing.FontStyle]::Regular)
$brushGray = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(214, 211, 209))
$g.DrawString('5 modeli rolb elektrycznych LiFePO4 • serwis w Polsce', $fontSub, $brushGray, 90, 490)
$brushGray.Dispose()
$fontSub.Dispose()

# === URL (bottom right) ===
$fontUrl = New-Object System.Drawing.Font 'Consolas', 24, ([System.Drawing.FontStyle]::Bold)
$brushUrl = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::White)
$sizeUrl = $g.MeasureString('sportice.pl', $fontUrl)
$g.DrawString('sportice.pl', $fontUrl, $brushUrl, ($w - $sizeUrl.Width - 90), ($h - $sizeUrl.Height - 50))
$brushUrl.Dispose()
$fontUrl.Dispose()

# === Thin red accent bar at bottom ===
$accent = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(217,35,43))
$g.FillRectangle($accent, 0, $h - 8, $w, 8)
$accent.Dispose()

# === Save ===
$out = 'C:\Users\klimc\Desktop\Asystenci\gamak\marki\sport-ice\website\assets\images\og-sportice.png'
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()

$size = (Get-Item $out).Length
Write-Host "OG image saved: $out ($size B, ${w}x${h})"
