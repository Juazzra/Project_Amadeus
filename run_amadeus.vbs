Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Pindahkan direktori kerja aktif ke folder project agar path relatif (media, DB, config) ditemukan dengan benar
objShell.CurrentDirectory = strPath

' Jalankan Amadeus menggunakan pythonw.exe agar berjalan tanpa jendela hitam console command prompt
objShell.Run """" & strPath & "\.venv\Scripts\pythonw.exe"" """ & strPath & "\overlay.py""", 0, False
