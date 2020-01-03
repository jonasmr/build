#!/usr/bin/python
import os
import re
import sys
import subprocess
import time
import shlex

#   - multiple targets
# * - multiple configs
#   - multiple platforms
#   - .win32 suffix for commands
# * - _win32 suffix for dirs
#   - _win32 suffix for files
#   - recursive .dirs

configs = {}
platforms = {"win32":1, "linux":1, "osx":1}
default_config = ""

class Config:
	def __init__(self, name):
		self.extension = ""
		self.name = name
		self.cpps = set()
		self.mms = set()
		self.cs = set()
		self.asms = set()
		self.objs = set()
		self.metals = set()
		self.objraw = set()
		self.target = ""
		self.targets = set()
		self.paramz = {}




configs["__default"] = Config("__default")


def GetConfig(s):
	if s == "":
		s = "__default";
	return configs[s];



def MergeConfigs():
	default = configs["__default"]
	for cfg_name in configs:
		if cfg_name != "__default":
			cfg = configs[cfg_name]
			cfg.cpps = cfg.cpps | default.cpps
			cfg.mms = cfg.mms | default.mms
			cfg.cs = cfg.cs | default.cs
			cfg.asms = cfg.asms | default.asms
			cfg.objs = cfg.objs | default.objs
			cfg.metals = cfg.metals | default.metals
			cfg.objraw = cfg.objraw | default.objraw
			cfg.target = default.target

def GetTargetName(cfg):
	ext = ""
	if g_platform == "win32":
		ext = ".exe"
	if cfg.name != default_config:
		return "%s.%s%s" % (cfg.target, cfg.name, ext)
	else:
		return "%s%s" % (cfg.target, ext)


g_platform = sys.platform

if g_platform == "darwin":
	g_platform = "osx"

if g_platform == "linux2":
	g_platform = "linux"

g_win32sdk = ""
g_win32InstallationPath = ""
g_win32VersionPath = ""
g_win32VCVersionNumber = ""
g_win32sdkInclude = ""
g_win32sdkLib = "" 
g_win32CLPath = "";
g_win32LinkPath = "";
g_win32VCPath = ""



paths_processed = set()

def SplitPath(p):
	idx_ext = p.rfind('.')
	idx_path = max(p.rfind('\\'), p.rfind('/'))
	extension_less = p
	extension = ""
	if idx_ext > idx_path:
		extension_less = p[:idx_ext];
		extension = p[idx_ext+1:];
	idx_platform = extension_less.rfind('_')
	platform = ""
	if idx_platform > idx_path:
		platform = extension_less[idx_platform+1:]
	#print( "Base '%s' :: extension '%s' platform '%s' debug '%s' " % (p, extension, platform, extension_less) )
	return extension, platform;

def SplitCommand(c):
	idx_platform = c.rfind('.');
	platform = ""
	command = c
	if idx_platform > 0:
		platform = c[idx_platform+1:]
		command = c[:idx_platform];
	#print("Split Command '%s' :: c '%s' plat '%s'" % (c, command, platform))
	return command, platform;

def SplitCommand3(c):
	platform = ""
	config = ""
	c1 = ""
	command, c0 = SplitCommand(c)
	if c0 != "":
		command, c1 = SplitCommand(command)
	if c0 in platforms:
		platform = c0
	if c0 in configs:
		config = c0
	if c1 in platforms:
		platform = c1
	if c1 in configs:
		config = c1
	return command, platform, config


def PlatformMatch(p):
	return p == "" or p == g_platform


def RunVSWhere(ExtraArgs):
	Result = {}
	if g_platform == "win32":
		ProgramFilesx84 = os.getenv("ProgramFiles(x86)");
		Path = "\"%s\\Microsoft Visual Studio\\Installer\\vswhere.exe\"%s" % (ProgramFilesx84, ExtraArgs);
		print(shlex.split(Path))
		Process = subprocess.Popen(args=shlex.split(Path), stdout=subprocess.PIPE)
		out, err = Process.communicate()
		Process.wait()
		lines = out.splitlines()
		for line in lines:
			l = line.decode('utf-8')
			l = l.strip()
			idx = l.find(":")
			if idx > 0:
				key = l[:idx]
				value = l[idx+2:]
				Result[key] = value
	return Result;

g_vswhere = {}
if g_platform == "win32":
	g_vswhere = RunVSWhere(" -products 'Microsoft.VisualStudio.Product.BuildTools'")
	if not "installationPath" in g_vswhere:
		g_vswhere = RunVSWhere("")
	g_win32InstallationPath = g_vswhere["installationPath"]
	g_win32VersionPath = "%s\\VC\\Auxiliary\\Build\\Microsoft.VCToolsVersion.default.txt" % g_win32InstallationPath
	with open(g_win32VersionPath) as f:
		g_win32VCVersionNumber = ''.join(f.read().split())




g_win32CLPath = "%s\\VC\\Tools\\MSVC\\%s\\bin\\HostX64\\x64\\cl.exe" % (g_win32InstallationPath, g_win32VCVersionNumber)
g_win32LinkPath = "%s\\VC\\Tools\\MSVC\\%s\\bin\\HostX64\\x64\\link.exe" % (g_win32InstallationPath, g_win32VCVersionNumber)
g_win32VCPath = "%s\\VC\\Tools\\MSVC\\%s" % (g_win32InstallationPath, g_win32VCVersionNumber)


def ProcessPath(d, cfg):
	abspth = os.path.abspath(d)
	extension, platform = SplitPath(abspth)
	if PlatformMatch(platform):
		if not abspth in paths_processed:
			paths_processed.add(abspth)
			for filename in os.listdir(abspth):
				p = os.path.join(d, filename)
				extension, platform = SplitPath(p)
				if PlatformMatch(platform):
					if extension == "cpp":
						cfg.cpps.add(p)
						print("cpp " + p)
					if extension == "mm":
						cfg.mms.add(p)
						print("mm " + p)
					if extension == "metal":
						cfg.metals.add(p)
						print("metal " + p)
					if extension == "s":
						cfg.asms.add(p)
						print("asm " + p)


def fixname(name, ext, cfg):
	rawbase = os.path.basename(name)[:-len(ext)]
	raw = rawbase
	idx = 0
	while raw in cfg.objraw:
		raw = "%s_%d" %(rawbase, idx)
		idx = idx + 1
	cfg.objraw.add(raw)
	objname = "$builddir/" + cfg.name + "/" + raw
	return objname, name

def AddParam(Param, V, config = ""):
	#print("--> '" + Param + "' '" + V +"'")
	cfg = GetConfig(config)
	value = cfg.paramz.get(Param, "");
	l1 = value
	value = value.strip() + " " + V;
	cfg.paramz[Param] = value;

def AddToEnv(Name, Value):
	Current = os.environ[Name]
	New = Current + "" + Value
	os.environ[Name] = New

with open("ngen.cfg") as f:
	for line in f:
		line = line.strip()
		if len(line) > 0 and line[0] != '#':
			IsCommand = line[0] == '.'
			if IsCommand:
				line = line[1:].strip()
			idx = line.find(' ')
			if idx < 1:
				continue
			command = line[:idx].strip()
			arg = line[idx+1:].strip()
			command, platform, config = SplitCommand3(command);
			cfg = GetConfig(config)
			print(" COMMAND ('%s' '%s' '%s') --> %s" % (command, platform, config, arg))
			if IsCommand:
				if command == "config":
					print("!! Config " + arg)
					configs[arg] = Config(arg)
					if default_config == "":
						default_config = arg
						print("default config is now " + default_config)
				if command == "win32sdk":
					if g_platform == "win32":
						g_win32sdk = arg
						print("win32 SDK: " + g_win32sdk)
				if(command == "dir"):
					ProcessPath(arg, cfg)
				if(command == "target"):
					cfg.target = arg.strip();
					print("CFG TARGET IS " + cfg.target);
					cfg.targets.add(cfg.target)
			else:
				l0 = command
				l1 = arg
				if PlatformMatch(platform):
					AddParam(l0, l1, config);
					if config != "":
						AddParam(l0, "")


if g_win32sdk != "":
	g_win32sdkInclude = "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\%s" % g_win32sdk
	g_win32sdkLib = "C:\\Program Files (x86)\\Windows Kits\\10\\Lib\\%s" % g_win32sdk
	AddParam("cflags", "-I\"%s\\include\"" % g_win32VCPath)
	AddParam("cflags", "-I\"%s\\atlmfc\\include\"" % g_win32VCPath)
	AddParam("cflags", "-I\"%s\\ucrt\"" % g_win32sdkInclude)
	AddParam("cflags", "-I\"%s\\um\"" % g_win32sdkInclude)
	AddParam("cflags", "-I\"%s\\shared\"" % g_win32sdkInclude)
	AddParam("ldflags", "/LIBPATH:\"%s\\ucrt\\x64\"" % g_win32sdkLib);
	AddParam("ldflags", "/LIBPATH:\"%s\\um\\x64\"" % g_win32sdkLib);
	AddParam("ldflags", "/LIBPATH:\"%s\\lib\\x64\"" % g_win32VCPath)


MergeConfigs()


def AddRule(f, str):
	for cfg_name in configs:
		if cfg_name != "__default":
			f.write(str.replace("%%", cfg_name))

with open("build.ninja", "w") as f:
	f.write("\n# Generated by ngen.py\n\n")
	if g_platform == "win32":
		f.write("cxx = " + g_win32CLPath + "\n\n")
	else:
		f.write("cxx = clang++\n\n")
	f.write("builddir = build\n\n")
	
	if g_platform == "win32":
		f.write("link = " + g_win32LinkPath + "\n")

	for cfg_name in configs:
		suffix = "";
		# if cfg_name != "__default":
		# 	suffix = "." + cfg_name
		cfg = configs[cfg_name]
		for key in configs["__default"].paramz.keys():
			value = cfg.paramz.get(key, "")
			if cfg_name != "__default":
				f.write( "%s_%s = $%s %s\n" % (key.strip(), cfg_name, key.strip(), value.strip()))
			else:
				f.write( "%s = %s\n" % (key.strip(), value.strip()))
		f.write("\n")

	if g_platform == "osx" or g_platform == "linux":
		AddRule(f, """rule cxx_%%
  command = $cxx -MMD -MT $out -MF $out.d $cflags_%% -c $in -o $out
  description = CXX $out
  depfile = $out.d
  deps = gcc

""")

		AddRule(f, """rule asm_%%
  command = as -masm=intel $in -o $out
  description = ASM $out

""")

		AddRule(f, """rule mxx_%%
  command = $cxx -MMD -MT $out -MF $out.d $cflags_%% $mmflags_%% -c $in -o $out
  description = CXX $out
  depfile = $out.d
  deps = gcc

""")

		AddRule(f, """rule link_%%
  command = $cxx $ldflags_%% -o $out $in $libs
  description = LINK $out

""")
		AddRule(f, """rule metal_%%
  command = xcrun -sdk macosx metal $in -o $out 
  description = METAL $out

""")

		AddRule(f, """rule metallib_%%
  command = xcrun -sdk macosx metallib $in -o $out 
  description = METAL $out

""")
	elif g_platform == "win32":
		AddRule(f, """rule cxx_%%
  command = $cxx /showIncludes /c $in /Fo$out $cflags_%%
  description = CXX $out
  depfile = $out.d
  deps = msvc

""")
		AddRule(f, """rule link_%%
  command = $link $ldflags /OUT:$out $in $libs
  description = LINK $out

""")

	f.write("""rule ngen
  command = python ngen.py

""")

	for cfg_name in configs:
		if cfg_name != "__default":
			cfg = configs[cfg_name]
			for v in cfg.cpps:
				objname, fullname = fixname(v, ".cpp", cfg)
				cfg.objs.add(objname+".o")
				f.write("build %s: cxx_%s %s\n" % (objname+".o", cfg_name, fullname))

			for v in cfg.mms:
				objname, fullname = fixname(v, ".mm", cfg)
				cfg.objs.add(objname+".o")
				f.write("build %s: mxx_%s %s\n" % (objname+".o", cfg_name, fullname))

			for v in cfg.asms:
				objname, fullname = fixname(v, ".s", cfg)
				cfg.objs.add(objname+".o")
				f.write("build %s: asm_%s %s\n" % (objname+".o", cfg_name, fullname))

			for v in cfg.metals:
				objname, fullname = fixname(v, ".metal", cfg)
				f.write("build %s: metal_%s %s\n" % (objname+".air", cfg_name, fullname))
				f.write("build %s: metallib_%s %s\n" % (objname+".metallib", cfg_name, objname+".air"))
				cfg.targets.add(objname+".metallib")
			ext = ""

			if g_platform == "win32":
				ext = ".exe"
			f.write("build %s: link_%s" % (GetTargetName(cfg), cfg_name))
			for obj in cfg.objs:
				f.write(" " + obj)
			f.write("\n\n")

	f.write("build build.ninja: ngen ngen.cfg\n\n");

	f.write("default build.ninja %s\n\n" % GetTargetName(configs[default_config]));

	for cfg_name in configs:
		if cfg_name != "__default":
			cfg = configs[cfg_name];
			f.write("build %s: phony %s\n" % (cfg_name, GetTargetName(cfg)))



	f.write("build all: phony ");
	for cfg_name in configs:
		if cfg_name != "__default":
			cfg = configs[cfg_name];
			f.write("%s " % GetTargetName(cfg));

	f.write("\n\n")
