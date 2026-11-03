"""Recover static reflection metadata in a bounded, isolated CPU emulator.

Only local PE bytes enter Unicorn. No executable entrypoint, game process,
operating-system API, injection, or network interface is used.
"""
import sys,struct,json,time,pathlib,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'.tools/python'))
import pefile,unicorn
from unicorn.x86_const import *
b=pathlib.Path('data/install/Shipping.exe').read_bytes();pe=pefile.PE(data=b,fast_load=True);base=pe.OPTIONAL_HEADER.ImageBase
if hashlib.sha256(b).hexdigest() != '619e4753e2f68c721764a19afe61b01daee723beaa946ef94ec6bb4e0c7c5747':
 raise ValueError('Unsupported game build; review reflection helper addresses first')
u=unicorn.Uc(unicorn.UC_ARCH_X86,unicorn.UC_MODE_64);u.mem_map(base,(pe.OPTIONAL_HEADER.SizeOfImage+4095)&~4095);u.mem_write(base,b[:pe.OPTIONAL_HEADER.SizeOfHeaders])
for s in pe.sections:
 if s.SizeOfRawData:u.mem_write(base+s.VirtualAddress,b[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData])
STACK=0x7000000000;STOP=0x7100000000;POOL=0x7200000000
u.mem_map(STACK,0x400000);u.mem_map(STOP,4096);u.mem_map(POOL,0x100000)
names=['None'];nameids={'None':0};capture=[]
def ret(uc,result=0):
 sp=uc.reg_read(UC_X86_REG_RSP);ra=struct.unpack('<Q',uc.mem_read(sp,8))[0];uc.reg_write(UC_X86_REG_RAX,result);uc.reg_write(UC_X86_REG_RSP,sp+8);uc.reg_write(UC_X86_REG_RIP,ra)
def hash_name(uc,a,z,d):ret(uc,0)
def get_pool(uc,a,z,d):ret(uc,POOL)
def store_name(uc,a,z,d):
 p=uc.reg_read(UC_X86_REG_R8);dest=uc.reg_read(UC_X86_REG_RDX);ptr,n,flags=struct.unpack('<QII',uc.mem_read(p,16));n=min(n,2048);wide=flags&1
 data=bytes(uc.mem_read(ptr,n*(2 if wide else 1)))
 try:name=data.decode('utf-16le' if wide else 'utf-8')
 except UnicodeError:name=data.decode('latin1')
 if name not in nameids:nameids[name]=len(names);names.append(name)
 nid=nameids[name];uc.mem_write(dest,struct.pack('<II',nid,0));capture.append(name);ret(uc,dest)
def noop(uc,a,z,d):ret(uc)
for rva,fn in [(0x4bb1450,hash_name),(0x4b9fbb0,get_pool),(0x4b9fa30,store_name),(0xe6ceb20,noop)]:
 u.hook_add(unicorn.UC_HOOK_CODE,fn,begin=base+pe.get_rva_from_offset(rva),end=base+pe.get_rva_from_offset(rva))
def run(rva):
 sp=STACK+0x3f0000;u.mem_write(sp,struct.pack('<Q',STOP));u.reg_write(UC_X86_REG_RSP,sp);u.reg_write(UC_X86_REG_RBP,0);u.reg_write(UC_X86_REG_RCX,0);u.reg_write(UC_X86_REG_RDX,0);u.reg_write(UC_X86_REG_R8,0);u.reg_write(UC_X86_REG_R9,0)
 try:
  u.emu_start(base+rva,STOP,count=15000)
  return u.reg_read(UC_X86_REG_RIP)==STOP,None
 except unicorn.UcError as e:return False,(str(e),hex(u.reg_read(UC_X86_REG_RIP)-base))
if len(sys.argv)>1:
 rva=pe.get_rva_from_offset(int(sys.argv[1],16));print('run',run(rva),'names',capture)
 print('Vector.X',bytes(u.mem_read(base+0x11e60320,56)).hex())
else:
 # Native .CRT$XCU initializer pointer range identified from the PE. Process only
 # these isolated helpers, never the executable entrypoint or a game process.
 off=0xeaa0da8;count=0
 text=pe.sections[0]
 while count < 200000:
  ptr=struct.unpack_from('<Q',b,off+count*8)[0]
  if not base+text.VirtualAddress <= ptr < base+text.VirtualAddress+text.Misc_VirtualSize: break
  count+=1
 stats_unused=None;stats={'ok':0,'fail':0};fails=[];t=time.monotonic()
 for j in range(count):
  ptr=struct.unpack_from('<Q',b,off+j*8)[0];ok,err=run(ptr-base);stats['ok' if ok else 'fail']+=1
  if not ok and len(fails)<150:fails.append([hex(ptr-base),err])
  if j%5000==0:print(j,stats,'names',len(names),'seconds',round(time.monotonic()-t,1),flush=True)
 pathlib.Path('data/reflection-names.json').write_text(json.dumps(names))
 for s in pe.sections:
  if s.Name.startswith(b'.data'):pathlib.Path('data/reflection-data.bin').write_bytes(bytes(u.mem_read(base+s.VirtualAddress,s.Misc_VirtualSize)))
 pathlib.Path('data/reflection-report.json').write_text(json.dumps({'stats':stats,'failures':fails}))
 print('DONE',stats,'names',len(names),'seconds',round(time.monotonic()-t,1))
