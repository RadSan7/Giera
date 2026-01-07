#!/usr/bin/env python3
# fix_indent.py - Fix sword swing sound indentation

with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line with 'player.attacking = True' after line 1000
for i, line in enumerate(lines):
    if i > 1000 and 'player.attacking = True' in line:
        print(f"Found attacking line at {i+1}")
        
        # Check if next lines have the sword swing code
        if i+1 < len(lines) and ('Play sword swing' in lines[i+1] or 'sword_swing' in lines[i+1]):
            # Remove existing sword swing code (4 lines)
            end_idx = i + 1
            while end_idx < len(lines) and ('sword_swing' in lines[end_idx] or 'Play sword' in lines[end_idx]):
                end_idx += 1
            print(f"Removing lines {i+2} to {end_idx}")
            del lines[i+1:end_idx]
        
        # Insert correctly indented sound code
        # player.attacking line has 25 spaces, so we match that
        sound_code = [
            '                         # Play sword swing sound\n',
            "                         if 'sword_swing' in sfx_sounds:\n",
            "                             sfx_sounds['sword_swing'].set_volume(0.6)\n",
            "                             sfx_sounds['sword_swing'].play()\n"
        ]
        
        for idx, sound_line in enumerate(sound_code):
            lines.insert(i + 1 + idx, sound_line)
        
        print("Inserted new sound code")
        break

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
    
print("Done!")
