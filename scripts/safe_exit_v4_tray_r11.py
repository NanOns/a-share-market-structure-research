"""Send the existing verified tray its implemented graceful session-end event."""
import argparse,ctypes,json,sys,time
from ctypes import wintypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);args=parser.parse_args()
    from workbench_desktop.storage import verified_existing_owner
    import psutil
    owner=verified_existing_owner(args.root)
    process=psutil.Process(owner['pid']);handle=owner.get('tray_hwnd')
    if not handle:raise ValueError('VERIFIED_TRAY_WINDOW_REQUIRED')
    user=ctypes.windll.user32
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    pid=wintypes.DWORD()
    if not user.GetWindowThreadProcessId(handle,ctypes.byref(pid)) or pid.value!=owner['pid']:raise ValueError('TRAY_WINDOW_PID_CHANGED')
    # The application explicitly maps WM_ENDSESSION to quiesce + safe exit.
    # This is a programmatic shutdown request, not evidence of a Windows reboot.
    if not user.PostMessageW(handle,0x0016,1,0):raise OSError('TRAY_SAFE_EXIT_MESSAGE_FAILED')
    try:process.wait(timeout=60)
    except psutil.TimeoutExpired:raise ValueError('WAITING_SAFE_BOUNDARY_NO_FORCE_TERMINATION')
    print(json.dumps(dict(status='GRACEFUL_TRAY_EXIT',pid=owner['pid'],forced=False,windows_reboot=False)))

if __name__=='__main__':main()
