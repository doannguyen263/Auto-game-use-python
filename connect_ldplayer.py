"""
Helper script to connect to LDPlayer
"""
import subprocess
import sys
import os

def find_ldplayer_adb():
    """Find LDPlayer ADB executable"""
    paths = [
        r"C:\LDPlayer\LDPlayer4.0\adb.exe",
        r"C:\LDPlayer\LDPlayer\adb.exe",
        r"C:\LDPlayer64\LDPlayer4.0\adb.exe",
        r"C:\LDPlayer64\LDPlayer\adb.exe",
        os.path.expanduser(r"~\LDPlayer\LDPlayer4.0\adb.exe"),
        os.path.expanduser(r"~\LDPlayer\LDPlayer\adb.exe"),
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def connect_ldplayer():
    """Connect to LDPlayer"""
    print("Đang tìm LDPlayer...")
    
    # Try to find LDPlayer ADB
    ldplayer_adb = find_ldplayer_adb()
    
    if ldplayer_adb:
        print(f"Tìm thấy LDPlayer ADB: {ldplayer_adb}")
        adb_path = ldplayer_adb
    else:
        print("Không tìm thấy LDPlayer ADB, sử dụng ADB hệ thống...")
        adb_path = "adb"
    
    # Try common LDPlayer ports
    ports = [5555, 5557, 5565, 5575, 5585]
    
    for port in ports:
        print(f"Đang thử kết nối port {port}...")
        try:
            result = subprocess.run(
                [adb_path, "connect", f"127.0.0.1:{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
                print(f"✓ Đã kết nối đến port {port}")
                
                # Verify connection
                result = subprocess.run(
                    [adb_path, "devices"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                print("\nDanh sách thiết bị:")
                print(result.stdout)
                
                devices = [line.split()[0] for line in result.stdout.strip().split('\n')[1:] 
                          if line.strip() and 'device' in line and f":{port}" in line]
                
                if devices:
                    print(f"\n✓ Kết nối thành công! Device: {devices[0]}")
                    return True
        except Exception as e:
            print(f"Lỗi khi kết nối port {port}: {e}")
            continue
    
    print("\n✗ Không thể kết nối đến LDPlayer")
    print("\nHướng dẫn:")
    print("1. Đảm bảo LDPlayer đang chạy")
    print("2. Mở LDPlayer Settings → Advanced → Enable ADB")
    print("3. Hoặc thử kết nối thủ công:")
    print("   adb connect 127.0.0.1:5555")
    
    return False

if __name__ == "__main__":
    success = connect_ldplayer()
    sys.exit(0 if success else 1)

