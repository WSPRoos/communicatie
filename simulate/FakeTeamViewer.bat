@echo off
REM Nep TeamViewer.exe voor Windows: logt de aanroep en sluit af.
REM Te gebruiken als "teamviewer_exe" in settings.json met simulate = true
REM (of laat de app het Python-simulatiescript aanroepen).
powershell -NoProfile -Command "$e = @{timestamp=(Get-Date -Format o); argv=$args} | ConvertTo-Json -Compress; Add-Content -Path '%~dp0fake_teamviewer.log' -Value $e" %*
echo FAKE TeamViewer gestart met argumenten: %*
