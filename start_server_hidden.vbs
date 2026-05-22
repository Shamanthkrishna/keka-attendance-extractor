Set WshShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

Dim projectDir
projectDir = "D:\Shamanth_Krishna\Other\Keka Attendance Extractor"

' Kill any existing instance on port 5000 silently
WshShell.Run "cmd /c for /f ""tokens=5"" %a in ('netstat -aon ^| findstr "":5000 ""') do taskkill /F /PID %a", 0, True

' Start the Flask server completely hidden (0 = no window)
WshShell.Run "pythonw """ & projectDir & "\server.py""", 0, False
