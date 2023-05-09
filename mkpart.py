#!/usr/bin/python3
#
import os, sys
import subprocess as subp

if len(sys.argv) < 2:
    print("A block device must be specified")
    quit(1)
devname = sys.argv[1]

partshow = f"sudo parted {devname} unit s print"
comp = subp.run(partshow, shell=True, text=True, capture_output=True)
if comp.returncode != 0:
    errmsg = comp.stderr.rstrip('\n')
    print(errmsg)
    quit(2)

fields = ('Number', 'Start', 'End', 'Size', 'File system', 'Name', 'Flags')
mesg = comp.stdout.rstrip('\n')
fix = False
label = 'gpt'
info_lines = mesg.split('\n')
field_idxs = []
part_cmds = []
for ln in info_lines:
    if ln.find('Partition Table:') == 0:
        label = ln.split()[2]
    elif ln.find('Number') == 0:
        for mark in fields:
            idx = ln.find(mark)
            if idx == -1:
                print(f'Invalid Title Line: {ln}')
                quit(4)
            field_idxs.append(idx)
    try:
        int(ln.split()[0])
    except:
        continue
    ptcmd = {}
    ptcmd['Number'] = ln[:field_idxs[1]].rstrip()
    ptcmd['Start'] = ln[field_idxs[1]:field_idxs[2]].rstrip()
    ptcmd['End'] = ln[field_idxs[2]:field_idxs[3]].rstrip()
    ptcmd['Size'] = ln[field_idxs[3]:field_idxs[4]].rstrip()
    ptcmd['Fs'] = ln[field_idxs[4]:field_idxs[5]].rstrip()
    ptcmd['Name'] = ln[field_idxs[5]:field_idxs[6]].rstrip()
    ptcmd['Flags'] = ln[field_idxs[6]:].rstrip()
    part_cmds.append(ptcmd)
    
if label != 'gpt':
    print(f'Label must be GPT, not {label}')
    quit(5)

with open("/tmp/parted.cmd", "w") as fout:
    fout.write(f'mklabel {label}\n');
    ptnum = 0
    lastpt = part_cmds[-1]
    for ptcmd in part_cmds:
        if ptcmd != lastpt:
            fout.write(f'mkpart {ptcmd["Name"]} {ptcmd["Start"]} {ptcmd["End"]}\n')
        else:
            fout.write(f'mkpart {ptcmd["Name"]} {ptcmd["Start"]} -1\n')
        ptnum += 1
        if len(ptcmd["Flags"]) != 0 and ptnum != 1:
            fout.write(f'set {ptnum} {ptcmd["Flags"]} on\n')
    fout.write('set 1 boot on\n')
    fout.write('set 1 esp on\n')

quit(0)
