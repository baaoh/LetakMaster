Set WshShell = CreateObject("WScript.Shell") 
If WScript.Arguments.Count = 0 Then 
    WScript.Quit 
End If 

' Reconstruct the command line arguments
command = ""
For Each arg In WScript.Arguments
    ' We need to handle quotes if the argument contains spaces
    If InStr(arg, " ") > 0 Then
        command = command & """" & arg & """ "
    Else
        command = command & arg & " "
    End If
Next

' Run the command hidden (0) and don't wait (False)
WshShell.Run command, 0, False
