import os

possible_paths = [
    r"C:\Program Files\Microsoft Office",
    r"C:\Program Files (x86)\Microsoft Office"
]

for base in possible_paths:
    for root, dirs, files in os.walk(base):
        for file in files:
            if file.lower() == "outlook.exe":
                print("✅ Encontrado:", os.path.join(root, file))
