Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
python tui_app.py @args
