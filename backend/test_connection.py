import sys
import pyodbc

print("Testing ODBC connection to MSSQLSERVER01...")
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost\\MSSQLSERVER01;"
    "DATABASE=QuanLyKhachSan;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 5 MaPhong, SoPhong, TinhTrang FROM Phong")
    rows = cursor.fetchall()
    print("SUCCESS: Connected to SQL Server! Sample rooms:")
    for r in rows:
        print(f" - {r.MaPhong}: Số phòng {r.SoPhong}, Tình trạng: {r.TinhTrang}")
    conn.close()
except Exception as e:
    print("ODBC Error:", e)
    print("\nTrying with Driver 17...")
    try:
        conn_str_17 = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=localhost\\MSSQLSERVER01;"
            "DATABASE=QuanLyKhachSan;"
            "Trusted_Connection=yes;"
            "TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str_17, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 5 MaPhong, SoPhong, TinhTrang FROM Phong")
        rows = cursor.fetchall()
        print("SUCCESS with Driver 17! Sample rooms:")
        for r in rows:
            print(f" - {r.MaPhong}: Số phòng {r.SoPhong}, Tình trạng: {r.TinhTrang}")
        conn.close()
    except Exception as e2:
        print("Driver 17 Error:", e2)

