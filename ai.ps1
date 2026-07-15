Set-Location -Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
python tui.py @args
