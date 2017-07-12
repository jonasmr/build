#!/usr/bin/python
import os
import re
cpps = set()
mms = set()
cs = set()
objs = set()
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
				print "mm " + p
			if p.endswith("c"):
				print "c " + p


def fixname(name, ext):

	objname = "$builddir/" + os.path.basename(name)[:-len(ext)] + ".o"
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

	f.write("""rule link
  command = $cxx $ldflags -o $out $in $libs
  description = LINK $out

""")
	for v in cpps:
		objname, fullname = fixname(v, ".cpp")
		objs.add(objname)
		f.write("build %s: cxx %s\n" % (objname, fullname))

	f.write("build out: link")
	for obj in objs:
		f.write(" " + obj)
	f.write("\n\n")

	f.write("default out\n\n");




