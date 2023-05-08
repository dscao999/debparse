#!/usr/bin/python3
#
import os
import sys
import time
import subprocess as subp
import shutil

isodir = '/'

illpkg = ['perlapi-5.32.0', 'libgcc1', 'libva-driver-abi-1.8', 'libva-driver-abi-1.10', 'libtime-local-perl', \
        'perl-openssl-abi-1.1', 'libnet-perl', 'libtest-simple-perl', 'libreoffice-core-nogui', \
        'libjs-normalize.css']
cycle_list = [('libc6', 'libgcc-s1'), ('libdevmapper-event1.02.1', 'dmsetup'), ('tasksel', 'tasksel-data')]
installed = []
pkg_deps = []
recursive = 0

def do_install(pname):
    global installed

    installed.append(pname)

def is_cyclic(pname):
    global cycle_list

    circle = False
    cycle = ()
    for cycle in cycle_list:
        for name in cycle:
            if pname == name:
                circle = True
                break;
    if circle:
        for pkg in cycle:
            do_install(pkg)
        print(f"Installed Cyclic Dependencies: {cycle}")
    return circle

def is_installed(pname):
    for ipkg in installed:
        if pname == ipkg:
            return True
    for ipkg in illpkg:
        if pname == ipkg:
            return True

    return False

def install_pkg(pname, pdeps):
    global recursive, pkg_deps, cycles

    recursive += 1
    if (recursive > 15):
        print(f'Recursion depth: {recursive}')
        quit(11)

    if is_installed(pname):
        recursive -= 1
        return
    if is_cyclic(pname):
        recursive -= 1
        return

    for dep in pdeps:
        if is_installed(dep):
            continue
        for depp in pkg_deps:
            if depp['name'] == dep:
                break
        if depp['name'] != dep:
            print(f'Fatal Error! Cannot find {dep} in package list')
        else:
            install_pkg(dep, depp['deps'])

    do_install(pname)
    print(f'Installed  {pname}')
    recursive -= 1

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
    print("An ISO file or a ISO mount point directory must be specified")
    quit(1)

if not os.path.isfile(isofile) and not os.path.ismount(isofile):
    print(isofile + " does not exist, or is not a mount point")
    quit(2)

if os.path.ismount(isofile):
    isodir = isofile
elif os.path.exists(isodir):
    print(f"Path {isodir} already exists. Please remove it first.")
    quit(3)
else:
    os.mkdir(isodir)
    comp = subp.run(f"sudo mount -o ro {curdir}/{isofile} {isodir}", shell=True, text=True, capture_output=True)
    if comp.returncode == 0:
        print(f"{isofile} mounted onto {isodir}")
    else:
        print(f"Cannot mount {isofile}")
        os.rmdir(isodir)
        quit(4)

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
        pkg_deps.append(debinfo[1])
    else:
        print(f'Package: {pkgname} info missing')

print("==============Package Information==================")
for pkg in pkg_deps:
    pname = pkg['name']
    pdeps = pkg['deps']
    if is_installed(pname):
        continue
    recursive = 0
    install_pkg(pname, pdeps);

if not os.path.ismount(isofile):
    comp = subp.run(f"sudo umount {isodir}", shell=True, text=True, capture_output=True)
    if comp.returncode != 0:
        errmsg = comp.stderr.rstrip('\n')
        print(f"Cannot umount {isodir}: {errmsg}")
    else:
        os.rmdir(isodir)

quit(0)
