Output demo/demo.gif
Output demo/demo.webm

Set Shell "bash"
Set FontSize 14
Set Width 90
Set Height 30
Set Theme "Molokai"
Set WindowBar Colorful
Set WindowBarSize 40
Set Padding 15
Set TypingSpeed 40ms

Type "# space-hog: Find what's eating your disk"
Enter
Sleep 500ms

Type "space-hog --advise 2>&1 | head -40"
Enter
Sleep 30s

Type "# Cleanup stats"
Enter
Sleep 500ms

Type "space-hog --stats"
Enter
Sleep 5s

Sleep 2s
