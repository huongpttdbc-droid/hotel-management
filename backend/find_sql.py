import subprocess
import winreg

print("=== Checking Registry for SQL Server Instances ===")
try:
    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Microsoft SQL Server\Instance Names\SQL")
    i = 0
    while True:
        try:
            name, val, _ = winreg.EnumValue(key, i)
            print(f"Instance: {name} -> {val}")
            i += 1
        except OSError:
            break
except Exception as e:
    print("Registry check error:", e)

print("\n=== Checking running tasklist ===")
out = subprocess.check_output(["tasklist", "/svc", "/fi", "imagename eq sqlservr.exe"]).decode("cp1252", errors="ignore")
print(out)

