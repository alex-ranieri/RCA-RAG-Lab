"""Medições Windows pela biblioteca padrão, sem dependências de monitoramento."""
import ctypes
import os

def memory_snapshot():
    if os.name != 'nt':
        return {'available': False}
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in
            ('total','free','page_total','page_free','virtual_total','virtual_free','extended')]
    m=Memory(); m.length=ctypes.sizeof(m)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
        return {'available': False}
    return {'available':True,'ram_total_mib':round(m.total/2**20,1),
            'ram_available_mib':round(m.free/2**20,1),'memory_load_percent':m.load,
            'commit_total_mib':round((m.page_total-m.page_free)/2**20,1)}
