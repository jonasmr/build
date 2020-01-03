#!/usr/bin/python
import os
import re
cpps = set()
mms = set()
cs = set()
asms = set()
objs = set()
metals = set()
objraw = set()
target = ""
targets = set()
paramz = {};

paths_processed = set()
def ProcessPath(d):
	abspth = os.path.abspath(d)
	if not abspth in paths_processed:
		paths_processed.add(abspth)
		for filename in os.listdir(abspth):
			p = os.path.join(d, filename)
			if p.endswith("cpp"):
				cpps.add(p)
				print "CPP " + p
			if p.endswith("mm"):
				mms.add(p)
			if p.endswith("metal"):
				metals.add(p)
			if p.endswith("s"):
				asms.add(p)


def fixname(name, ext):
	rawbase = os.path.basename(name)[:-len(ext)]
	raw = rawbase
	idx = 0
	while raw in objraw:
		raw = "%s_%d" %(rawbase, idx)
		idx = idx + 1
	objraw.add(raw)
	objname = "$builddir/" + raw
	return objname, name

with open("ngen.cfg") as f:
	for line in f:
		line = line.strip()
		if len(line) > 0 and line[0] != '#':
			if(line[0] == '.'):
				command = line[1:].strip()
				idx = command.find(' ')
				arg = command[idx+1:].strip()
				command = command[:idx]
				if(command == "dir"):
					ProcessPath(arg)
				if(command == "target"):
					target = arg.strip()
					targets.add(arg.strip())
			else:
				idx = re.search(r'[ =]', line).start()
				i = line.find('=')
				if i > 0:
					l0 = line[:i].strip()
					l1 = line[i+1:].strip()
					print "'" + l0 + "' :: '" + l1 +"'"
					value = paramz.get(l0, "");
					value = value + " " + l1;
					paramz[l0] = value;
					print  "'" + l0 + "' xxx '" + value +"'"


with open("build.ninja", "w") as f:
	for key,value in paramz.items():
		f.write( "%s = %s\n\n" % (key.strip(), value.strip()))
		print( "%s = %s" % (key.strip(), value.strip()))


	f.write("""rule cxx
  command = $cxx -MMD -MT $out -MF $out.d $cflags -c $in -o $out
  description = CXX $out
  depfile = $out.d
  deps = gcc

""")

	f.write("""rule asm
  command = as -masm=intel $in -o $out
  description = ASM $out

""")

	f.write("""rule mxx
  command = $cxx -MMD -MT $out -MF $out.d $cflags $mmflags -c $in -o $out
  description = CXX $out
  depfile = $out.d
  deps = gcc

""")

	f.write("""rule link
  command = $cxx $ldflags -o $out $in $libs
  description = LINK $out

""")
	f.write("""rule metal
  command = xcrun -sdk macosx metal $in -o $out 
  description = METAL $out

""")

	f.write("""rule metallib
  command = xcrun -sdk macosx metallib $in -o $out 
  description = METAL $out

""")


	f.write("""rule ngen
  command = ngen

""")



	for v in cpps:
		objname, fullname = fixname(v, ".cpp")
		objs.add(objname+".o")
		f.write("build %s: cxx %s\n" % (objname+".o", fullname))
	for v in mms:
		objname, fullname = fixname(v, ".mm")
		objs.add(objname+".o")
		f.write("build %s: mxx %s\n" % (objname+".o", fullname))

	for v in asms:
		objname, fullname = fixname(v, ".s")
		objs.add(objname+".o")
		f.write("build %s: asm %s\n" % (objname+".o", fullname))

	for v in metals:
		objname, fullname = fixname(v, ".metal")
		f.write("build %s: metal %s\n" % (objname+".air", fullname))
		f.write("build %s: metallib %s\n" % (objname+".metallib", objname+".air"))
		targets.add(objname+".metallib")


	f.write("build %s: link" %(target))
	for obj in objs:
		f.write(" " + obj)
	f.write("\n\n")

	f.write("build build.ninja: ngen ngen.cfg\n\n");


	f.write("default build.ninja " );
	for s in targets:
		f.write(" " + s)
	f.write("\n\n")




