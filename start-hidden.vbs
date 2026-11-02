' Starts the onlyfriends server (http://127.0.0.1:8766) with no console window (Windows).
' Localhost only. Needs pythonw on PATH. Put a shortcut to this file in shell:startup to autostart.
Option Explicit
Dim sh, fso
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)
sh.Run "pythonw serve.py", 0, False
