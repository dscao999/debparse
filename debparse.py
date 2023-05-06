#!/usr/bin/python3
#
import os
import sys
import time
import subprocess as subp
import shutil

isodir = '/'

def remove_vname(pkgname):
    if pkgname.find('(') == -1:
        return pkgname.strip(' ').rstrip(' ')
    vname = pkgname.split('(')
    return vname[0].strip(' ').rstrip(' ')

def get_debinfo(debfile, pkgname):
    expand = f"dpkg-deb --raw-extract {debfile} {pkgname}"
    comp = subp.run(expand, shell=True, text=True)
    if comp.returncode != 0:
        print(f"Cannot extract deb {debfile}")
        shutil.rmtree(pkgname)
        return (1, {})

    dep = 0
    ln = ''
    with open(f"{pkgname}/DEBIAN/control", "r") as fin:
        for ln in fin:
            if ln.find("Depends:") == 0:
                dep = 1
                break
    shutil.rmtree(pkgname)
    if dep == 0:
        return (0, {"name": pkgname, "deps": []})

    depline = ln.rstrip('\n').split(':')[1].strip(' ')
    depnames = depline.split(',')
    if len(depnames) == 0:
        return (0, {"name": pkgname, "deps": []})
    deplist = []
    for vname in depnames:
        if vname.find('|') == -1:
            deplist.append(remove_vname(vname))
            continue
        equals = vname.split('|')
        for eq in equals:
            name = remove_vname(eq)
            find =f"find {isodir}/pool -name {name}_\* -print"
            comp = subp.run(find, shell=True, text=True, capture_output=True)
            if comp.returncode != 0 or len(comp.stdout) == 0:
                print(f"No package {name}: Probably a virtual package")
                continue
            deplist.append(name)
            break

    return (0, {"name": pkgname, "deps": deplist})

isofile = sys.argv[-1]
isodir = "iso-" + str(os.getpid())
curdir = os.curdir

if len(sys.argv) == 1:
    print("An ISO file must be specified")
    quit(1)

if not os.path.isfile(isofile):
    print(isofile + " does not exist")
    quit(2)

if os.path.exists(isodir):
    print(f"Path {isodir} already exists. Please remove it first.")
    quit(3)

os.mkdir(isodir)
comp = subp.run(f"sudo mount -o ro {curdir}/{isofile} {isodir}", shell=True, text=True, capture_output=True)
if comp.returncode == 0:
    print(f"{isofile} mounted onto {isodir}")

seacmd = "dpkg --list|grep -E '^ii'|awk '{print $2}'"

comp = subp.run(seacmd, capture_output=True, shell=True, text=True)
if comp.returncode != 0:
    errmsg = comp.stderr.rstrip('\n')
    print(f"Cannot retrieve installed packages! {errmsg}")
    quit(comp.returncode)

pkginfo = comp.stdout.rstrip('\n').split('\n')
pkglist = []
for pkgname in pkginfo:
    pkgname = pkgname.split(':')[0]
    pkglist.append(pkgname)

deps = []
for pkgname in pkglist:
    find = f"find {isodir}/pool -name {pkgname}_\* -print"
    comp = subp.run(find, shell=True, text=True, capture_output=True)
    if comp.returncode != 0 or len(comp.stdout) == 0:
        errmsg = comp.stderr.rstrip('\n')
        print(f"find {pkgname} failed: {errmsg}")
        continue
    debfile = comp.stdout.rstrip('\n')
    debinfo = get_debinfo(debfile, pkgname)
    if debinfo[0] == 0:
        deps.append(debinfo[1])

print("==============Package Information==================")
for pkgs in deps:
    print(f"Package: {pkgs['name']} deps: {pkgs['deps']}")

comp = subp.run(f"sudo umount {isodir}", shell=True, text=True, capture_output=True)
if comp.returncode != 0:
    errmsg = comp.stderr.rstrip('\n')
    print(f"Cannot umount {isodir}: {errmsg}")
else:
    os.rmdir(isodir)

quit(0)
