import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/killerflux/voice_teleop_ws/install/voice_teleop'
