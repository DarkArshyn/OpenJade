"""Collect evidence for native follow-up; does not disassemble or execute the game."""
import argparse,hashlib,json,re,struct
from pathlib import Path


def pe_sections(data):
    if len(data)<64 or data[:2]!=b'MZ':raise ValueError('Not MZ')
    pe=struct.unpack_from('<I',data,60)[0]
    if pe+24>len(data) or data[pe:pe+4]!=b'PE\0\0':raise ValueError('Invalid PE')
    machine,n=struct.unpack_from('<HH',data,pe+4);opt=struct.unpack_from('<H',data,pe+20)[0]
    if machine!=0x14c or opt<32 or pe+24+opt+40*n>len(data):raise ValueError('Unsupported PE layout')
    if struct.unpack_from('<H',data,pe+24)[0]!=0x10b:raise ValueError('Not PE32')
    base=struct.unpack_from('<I',data,pe+24+28)[0];sections=[]
    for i in range(n):
        o=pe+24+opt+40*i;vsize,rva,size,offset=struct.unpack_from('<4I',data,o+8)
        if size and offset+size>len(data):raise ValueError('Truncated section')
        flags=struct.unpack_from('<I',data,o+36)[0]
        sections.append(dict(name=data[o:o+8].rstrip(b'\0').decode('ascii','replace'),rva=rva,offset=offset,size=size,executable=bool(flags&0x20000000)))
    return base,sections


def export(exe,tokens_path,output):
    data=exe.read_bytes();base,sections=pe_sections(data)
    digest=hashlib.sha256(data).hexdigest()
    if digest!='6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9':raise ValueError('Unsupported game binary')
    leads=[]
    for m in re.finditer(rb'[\x20-\x7e]{7,}',data):
        if not any(term in m.group() for term in [b'AI_ul_CallbackLoadVars',b'AI_gpst_DynAINodeStack',b'AI_gpast_DynAIFunctionTT']):continue
        section=next((s for s in sections if s['offset']<=m.start()<s['offset']+s['size']),None)
        if section is None:continue
        address=base+section['rva']+m.start()-section['offset'];needle=struct.pack('<I',address);matches=[]
        for s in sections:
            if not s['executable']:continue
            start=s['offset'];end=start+s['size']
            while (o:=data.find(needle,start,end))>=0:
                matches.append(dict(file_offset=o,preferred_va=base+s['rva']+o-s['offset']));start=o+1
        leads.append(dict(text=m.group().decode('ascii'),file_offset=m.start(),preferred_va=address,address_byte_matches=matches))
    source=json.loads(tokens_path.read_text(encoding='utf8'));motifs=[]
    for key,b in source['blocks'].items():
        t=b['tokens'];occ=[i for i,v in enumerate(t) if v['tag']==0x02000960]
        for i in occ:
            if i>=2 and t[i-1]['operand']==1720 and t[i-1]['tag']==0x14000025:
                motifs.append(dict(record=key,sequence=t[i-2:i+1]))
    output.mkdir(parents=True,exist_ok=False)
    (output/'follow-up.json').write_text(json.dumps(dict(executable_sha256=digest,image_base=base,sections=sections,native_leads=leads,vector_motifs=motifs,limitations=['Preferred addresses require relocation awareness','Address byte matches are not decoded xrefs','Opcode 0x02000960 has no verified semantics','No game execution or decompilation performed']),indent=2),encoding='utf8')
    print('Native string leads:',len(leads),'Vector motifs:',len(motifs),'Address-byte matches:',sum(len(x['address_byte_matches']) for x in leads))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('exe',type=Path);p.add_argument('tokens',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.exe,a.tokens,a.output)
