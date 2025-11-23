
lines = []
with open('src/models/database_model.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to delete lines 881 to 1079 (1-based)
# In 0-based index: 880 to 1078 (inclusive)
# So we keep 0 to 879, and 1079 to end.

new_lines = lines[:880] + lines[1079:]

with open('src/models/database_model.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed database_model.py")
