# Prompt Optimizer MCP — demo recording script
#
# Regenerate the README hero GIF with:
#   brew install charmbracelet/tap/vhs
#   vhs docs/demo.tape
#
# Output: docs/demo.gif (embedded in README.md)
# Prereq: `prompt-optimizer` CLI on PATH (pip install -e . or pipx install .)

Output docs/demo.gif

Set FontSize 14
Set Width 1200
Set Height 720
Set Theme "Dracula"
Set TypingSpeed 40ms
Set Padding 20

Type "# 1. Score any prompt in milliseconds — no API key."
Enter
Sleep 600ms

Type "prompt-optimizer 'write some code to handle users'"
Enter
Sleep 4s

Type "clear"
Enter
Sleep 400ms

Type "# 2. Iteratively improve until it hits a target score."
Enter
Sleep 600ms

Type "prompt-optimizer --loop 'make an api' --language python --target-score 40"
Enter
Sleep 5s

Type "clear"
Enter
Sleep 400ms

Type "# 3. JSON output — wire it into any agent pipeline."
Enter
Sleep 600ms

Type "echo 'fix the login bug' | prompt-optimizer --loop --json | jq '.final_score'"
Enter
Sleep 4s
