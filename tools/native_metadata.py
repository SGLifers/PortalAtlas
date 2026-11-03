"""Read the executable and its isolated reflection-initializer memory overlay."""
import json
import pathlib
import re
import struct
import numpy as np
import pefile


class Image:
    def __init__(self, root=pathlib.Path('.')):
        self.bytes=(root/'data/install/Shipping.exe').read_bytes()
        self.pe=pefile.PE(data=self.bytes,fast_load=True)
        self.base=self.pe.OPTIONAL_HEADER.ImageBase
        self.names=json.loads((root/'data/reflection-names.json').read_text())
        self.sections={s.Name.rstrip(b'\0').decode():s for s in self.pe.sections}
        self.data=self.sections['.data'];self.rdata=self.sections['.rdata'];self.text=self.sections['.text']
        self.overlay=(root/'data/reflection-data.bin').read_bytes()

    def in_section(self,v,s):
        return (v>=self.base+s.VirtualAddress)&(v<self.base+s.VirtualAddress+s.Misc_VirtualSize)

    def read(self,v,n):
        r=int(v)-self.base
        if self.data.VirtualAddress<=r<self.data.VirtualAddress+self.data.Misc_VirtualSize:
            return self.overlay[r-self.data.VirtualAddress:r-self.data.VirtualAddress+n]
        try:
            offset=self.pe.get_offset_from_rva(r)
            return self.bytes[offset:offset+n] if offset>=0 else b''
        except (pefile.PEFormatError,ValueError):return b''

    def qword(self,v):return struct.unpack('<Q',self.read(v,8))[0]
    def fname(self,v):
        i=struct.unpack('<I',self.read(v,4))[0]
        return self.names[i] if i<len(self.names) else '?'

    def arrays(self):
        for section,blob in [(self.rdata,self.bytes[self.rdata.PointerToRawData:self.rdata.PointerToRawData+self.rdata.SizeOfRawData]),(self.data,self.overlay)]:
            yield self.base+section.VirtualAddress,np.frombuffer(blob[:len(blob)//8*8],dtype='<u8')

    def string(self,ptr,wide=False):
        data=self.read(ptr,240)
        try:
            value=data.decode('utf-16le').split('\0')[0] if wide else data.split(b'\0')[0].decode('ascii')
            return value if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9:]{0,100}',value) else None
        except UnicodeError:return None


def scan_class_params(image):
    rd=image.rdata;data=image.data;text=image.text;inside=image.in_section;result={}
    for addr,a in image.arrays():
        valid_config=(a[1:-6]<len(image.names))|inside(a[1:-6],rd)|inside(a[1:-6],data)
        mask=inside(a[:-7],text)&valid_config&(inside(a[2:-5],rd)|inside(a[2:-5],data))&(inside(a[3:-4],rd)|inside(a[3:-4],data))
        for offset in (4,5,6):mask&=(a[offset:offset+len(mask)]==0)|inside(a[offset:offset+len(mask)],rd)
        for i in np.flatnonzero(mask):
            values=[int(x) for x in a[i:i+8]];counts=values[7]&0xffffffff
            if counts&15<=3 and ((counts>>15)&2047)<1800:
                address=int(addr+i*8);result[address]={'address':address,'values':values,'props':(counts>>15)&2047,'flags':values[7]>>32}
    return result


def scan_struct_params(image):
    rd=image.rdata;text=image.text;inside=image.in_section;result={}
    for addr,a in image.arrays():
        mask=inside(a[:-6],text)&((a[1:-5]==0)|inside(a[1:-5],text))&((a[2:-4]==0)|inside(a[2:-4],text))&inside(a[3:-3],rd)&((a[4:-2]==0)|inside(a[4:-2],rd))
        for i in np.flatnonzero(mask):
            values=[int(v) for v in a[i:i+7]];name=image.string(values[3])
            if not name:continue
            count=values[5]&0xffff;alignment=values[5]>>32
            if count>2000 or alignment not in [1,2,4,8,16,32,64]:continue
            result[int(addr+i*8)]={'name':name,'superfn':values[1],'props':count,'array':values[4]}
    return result


def scan_registrations(image):
    # Native struct/enum compiled registration records preserve UTF-16 names.
    rd=image.rdata;text=image.text;data=image.data;inside=image.in_section;result={}
    addr,a=next(image.arrays())
    mask=inside(a[:-4],text)&inside(a[1:-3],text)&inside(a[2:-2],rd)&inside(a[3:-1],data)
    for i in np.flatnonzero(mask):
        name=image.string(int(a[i+2]),True) or image.string(int(a[i+2]))
        if name:result[int(a[i])]=name
    return result


def scan_enums(image):
    rd=image.rdata;text=image.text;data=image.data;inside=image.in_section;enums={}
    for addr,a in image.arrays():
        mask=inside(a[:-5],text)&((a[1:-4]==0)|inside(a[1:-4],text))&inside(a[2:-3],rd)&inside(a[3:-2],rd)&(inside(a[4:-1],rd)|inside(a[4:-1],data))&((a[5:]&0xffffffff)==0x45)
        for i in np.flatnonzero(mask):
            name=image.string(int(a[i+2]));count=(int(a[i+5])>>32)&0xffff
            if not name or not 0<count<4000:continue
            values={};array=int(a[i+4]);valid=True
            for k in range(count):
                raw=image.read(array+k*16,16)
                if len(raw)!=16:valid=False;break
                ptr,value=struct.unpack('<Qq',raw);label=image.string(ptr)
                if not label:valid=False;break
                values[value]=label
            if valid:enums[name]=values
    return enums
