"""Build CUE4Parse JSON schemas directly from the installed native metadata."""
import sys,pathlib,struct,re,json,functools,collections
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'.tools/python'))
import capstone
from native_metadata import Image,scan_class_params,scan_struct_params,scan_registrations,scan_enums
image=Image();b=image.bytes;p=image.pe;base=image.base;names=image.names
read=image.read;q=image.qword;fname=image.fname;insec=image.in_section;text=image.text
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64);md.detail=True
params=scan_class_params(image);structs=scan_struct_params(image);func_names=scan_registrations(image)
@functools.lru_cache(None)
def instructions(fn):
 code=read(fn,400);out=[]
 try:
  for ins in md.disasm(code,fn):
   out.append(ins)
   if ins.mnemonic=='ret':break
 except:pass
 return out
@functools.lru_cache(None)
def static_name(fn):
 for ins in instructions(fn):
  op=ins.operands
  if ins.mnemonic=='lea' and len(op)==2 and op[0].type==1 and op[0].reg==capstone.x86.X86_REG_RDX and op[1].type==3 and op[1].mem.base==capstone.x86.X86_REG_RIP:
   v=ins.address+ins.size+op[1].mem.disp
   try:n=read(v,160).decode('utf-16le').split('\0')[0]
   except:continue
   if re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,70}',n):return n
 return None
for v,x in params.items():
 n=static_name(x['values'][0])
 if n:x['name']=n;func_names[x['values'][0]]=n
@functools.lru_cache(None)
def fn_name(fn):
 if not fn:return None
 if fn in func_names:return func_names[fn]
 for ins in instructions(fn):
  op=ins.operands
  if ins.mnemonic=='lea' and len(op)==2 and op[1].type==3 and op[1].mem.base==capstone.x86.X86_REG_RIP:
   v=ins.address+ins.size+op[1].mem.disp
   if v in params:return params[v].get('name')
   if v in structs:return structs[v]['name']
 return static_name(fn)
types={};errors=[]
TYPES={0:'ByteProperty',1:'Int8Property',2:'Int16Property',3:'IntProperty',4:'Int64Property',5:'UInt16Property',6:'UInt32Property',7:'UInt64Property',8:'IntProperty',9:'UInt32Property',10:'FloatProperty',11:'DoubleProperty',12:'BoolProperty',13:'SoftClassProperty',14:'WeakObjectProperty',15:'LazyObjectProperty',16:'SoftObjectProperty',17:'ClassProperty',18:'ObjectProperty',19:'InterfaceProperty',20:'NameProperty',21:'StrProperty',22:'ArrayProperty',23:'MapProperty',24:'SetProperty',25:'StructProperty',26:'DelegateProperty',27:'MulticastInlineDelegateProperty',28:'MulticastSparseDelegateProperty',29:'TextProperty',30:'EnumProperty',31:'FieldPathProperty',32:'DoubleProperty',33:'OptionalProperty'}
def build(n,superfn,array,count):
 stack=[]
 for i in range(count):
  ptr=q(array+i*8);buf=read(ptr,80)
  if len(buf)<56:raise ValueError('truncated property')
  name=fname(ptr);flags=struct.unpack_from('<Q',buf,16)[0];gen=struct.unpack_from('<I',buf,24)[0]&63;arr,offset=struct.unpack_from('<HH',buf,48)
  if name in ['?','None']:raise ValueError(f'uninitialized property {i}/{count} at {ptr-base:x}')
  if gen not in TYPES:raise ValueError(f'unknown property type {gen}')
  mt={'type':TYPES[gen]}
  if gen==25:
   mt['structType']=fn_name(struct.unpack_from('<Q',buf,56)[0]) or 'Unknown'
  if gen in [22,24,33,30]:
   if not stack:raise ValueError('missing container inner')
   mt['innerType']=stack.pop()['mappingType']
   if gen==30:mt['enumName']=fn_name(struct.unpack_from('<Q',buf,56)[0]) or 'Unknown'
  if gen==23:
   if len(stack)<2:raise ValueError('missing map inners')
   key=stack.pop()['mappingType'];value=stack.pop()['mappingType'];mt.update(innerType=key,valueType=value)
  if gen==0:
   enumfn=struct.unpack_from('<Q',buf,56)[0]
   if enumfn and insec(enumfn,text):mt['enumName']=fn_name(enumfn) or 'Unknown';mt['isEnumAsByte']=True
  if flags&0x800000000:continue
  stack.append({'name':name,'arraySize':max(1,arr),'mappingType':mt})
 idx=0;props=[]
 for z in stack:
  z['index']=idx;idx+=z['arraySize'];props.append(z)
 return {'name':n,'superType':fn_name(superfn),'propertyCount':idx,'properties':props}
for x in params.values():
 n=x.get('name')
 if not n:continue
 vs=x['values'];dep=vs[7]&15;superfn=q(vs[3]) if dep>=2 else 0
 try:types[n]=build(n,superfn,vs[5],x['props'])
 except Exception as e:errors.append([n,str(e)])
for x in structs.values():
 n=x['name']
 try:types[n]=build(n,x['superfn'],x['array'],x['props'])
 except Exception as e:errors.append([n,str(e)])
json.dump(list(types.values()),open('data/mappings.json','w'))
enums=scan_enums(image)
json.dump(enums,open('data/mappings-enums.json','w'))
report={'errors':errors,'classParams':len(params),'namedClasses':sum('name' in x for x in params.values()),'structParams':len(structs),'types':len(types),'enums':len(enums)}
json.dump(report,open('data/mappings-report.json','w'))
print('Recovered schemas:',len(types),'enums:',len(enums),'rejected schemas:',len(errors))
for required in ['Actor','SceneComponent','PrimitiveComponent','StaticMeshComponent','Vector','GF1047PortalWall']:
 if required not in types:raise RuntimeError('Missing essential schema: '+required)
