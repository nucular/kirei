import os, sys, re
import xml.etree.ElementTree as ET
import configparser

SCHEMA_SVG = "{http://www.w3.org/2000/svg}"
SCHEMA_XLINK = "{http://www.w3.org/1999/xlink}"

LINUX = sys.platform.startswith("linux") or sys.platform.startswith("cygwin")
WINDOWS = sys.platform.startswith("win")
DARWIN = sys.platform.startswith("darwin")


# Adapted from the shlex module
_find_unsafe = re.compile(r'[^\w@%+=:,./-]', re.ASCII).search
def shellquote(s):
    if not s:
      if WINDOWS:
        return "\"\""
      else:
        return "''"
    if _find_unsafe(s) is None:
      return s

    if WINDOWS:
      # just give up
      return "\"" + s + "\""
    else:
      return "'" + s.replace("'", "'\"'\"'") + "'"

def targetquote(s):
  return s.replace(" ", "\\ ")


class Rasterizer(object):
  """
  Base class for all other Rasterizer classes, which provide a common interface
  for searching the executables of a rasterizer and generating appropriate
  commands to call them.
  """
  NAME = ""
  HELP = ""
  PRIORITY = float("-inf")

  EXECUTABLES = []
  SEARCHPATHS = []
  EXCLUDED = []

  def __init__(self, path):
    self.path = path

  def rasterizeCommand(self, inputpath, outputpath, scale):
    raise NotImplementedError()

  @classmethod
  def find(cls):
    # Adapted from http://stackoverflow.com/a/377028/2405983
    import os
    def isExecutable(fpath):
      return (not fpath in cls.EXCLUDED) and os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    for executable in cls.EXECUTABLES:
      if isExecutable(executable): return executable
      for path in os.environ["PATH"].split(os.pathsep):
        fpath = os.path.join(path.strip('"'), executable)
        if isExecutable(fpath):
          return cls(fpath)
      for path in cls.SEARCHPATHS:
        fpath = os.path.join(path, executable)
        if isExecutable(fpath):
          return cls(fpath)


class InkscapeRasterizer(Rasterizer):
  """
  Use the Inkscape command line interface, slow and unreliable (not recommended).
  """
  NAME = "inkscape"
  PRIORITY = 0

  if LINUX:
    EXECUTABLES = ["inkscape"]
  elif WINDOWS:
    EXECUTABLES = ["inkscape.exe"]
    SEARCHPATHS = ["C:\\Program Files\\Inkscape", "C:\\Program Files (x86)\\Inkscape"]
  elif DARWIN:
    EXECUTABLES = ["inkscape", "inkscape-bin"]
    SEARCHPATHS = ["/Applications/Inkscape.app/Contents/Resources/bin/inkscape"]

  def rasterizeCommand(self, inputFilepath, outputFilepath, scale):
    return "\"{0}\" {1} --export-dpi={2} --export-png={3}".format(
      shellquote(self.path),
      shellquote(inputFilepath),
      int(scale * 90),
      shellquote(outputFilepath)
    )


class ImageMagickRasterizer(Rasterizer):
  """
  Use the ImageMagick convert tool (recommended).
  """
  NAME = "imagemagick"
  PRIORITY = 2

  if LINUX:
    EXECUTABLES = ["convert"]
  elif WINDOWS:
    EXECUTABLES = ["convert.exe", "im-convert.exe"]
    EXCLUDE = ["C:\\Windows\\system32\\convert.exe"]
  elif DARWIN:
    EXECUTABLES = ["convert"]
    SEARCHPATHS = ["/opt/ImageMagick"]
  if "MAGICK_HOME" in os.environ:
    SEARCHPATHS.append(os.environ["MAGICK_HOME"])

  def rasterizeCommand(self, inputFilepath, outputFilepath, scale):
    return "{0} -density {1} -background none {2} {3}".format(
      shellquote(self.path),
      int(scale * 90),
      shellquote(inputFilepath),
      shellquote(outputFilepath)
    )


class RsvgRasterizer(Rasterizer):
  """
  Use the rsvg-convert tool, part of libRSVG.
  """
  NAME = "rsvg"
  PRIORITY = 1

  if WINDOWS:
    EXECUTABLES = ["rsvg-convert.exe"]
  else:
    EXECUTABLES = ["rsvg-convert"]

  def rasterizeCommand(self, inputFilepath, outputFilepath, scale):
    return "{0} -f png -z {1} -o {2} {3}".format(
      shellquote(self.path), scale,
      shellquote(outputFilepath),
      shellquote(inputFilepath)
    )


# Keeps a list of all rasterizers, sorted by their priority
allRasterizers = Rasterizer.__subclasses__()
allRasterizers.sort(key=lambda v: v.PRIORITY, reverse=True)


class Generator(object):
  """
  Generates a Makefile for building the Kirei osu! skin.
  """
  def __init__(self, args):
    self.output = args.output
    self.sourceDir = args.sourcedir
    self.buildDir = args.builddir

    self.depCache = {}

    if self.output == sys.stdout: self.log = sys.stderr
    else: self.log = sys.stdout

    config = configparser.ConfigParser()
    config.read(os.path.join(self.sourceDir, "skin.ini"))
    self.skinVersion = config["General"]["Name"].split(" ")[1]
    print("Skin version: {0}".format(self.skinVersion))

    for r in allRasterizers:
      if args.rasterizer != "auto":
        if args.rasterizer == r.NAME:
          if args.rasterizer_path:
            self.rasterizer = r(args.rasterizer_path)
          else:
            print("Searching for {0}...".format(r.NAME), file=self.log, end=" ")
            self.rasterizer = r.find()
      else:
        print("Searching for {0}...".format(r.NAME), file=self.log, end=" ")
        self.rasterizer = r.find()
        if self.rasterizer:
          break

    if self.rasterizer:
      print("Found.", file=self.log)
      print("Rasterizer: {0} ({1})".format(self.rasterizer.NAME, self.rasterizer.path), file=self.log)
    else:
      print("Not found.", file=self.log)
      print("No rasterizer found.", file=self.log)
      sys.exit(1)

  def emitTargetHead(self, name, phony=False, deps=[]):
    """Emits the head of a target, including PHONY declaration and dependencies."""
    print("Writing target: {0}".format(name), file=self.log)
    targetname = targetquote(name)
    targetdeps = [targetquote(i) for i in deps]
    if phony:
      self.output.write(".PHONY: {0}\n".format(targetname))
    self.output.write("{0}: {1}\n".format(targetname, " ".join(targetdeps)))
    return name

  def emitCommand(self, command):
    """Emits a command inside a target."""
    self.output.write("\t{0}\n".format(command))

  def collectSVGDeps(self, inputFilepath):
    """Parses an SVG file and returns the paths to all embedded images."""
    if inputFilepath in self.depCache:
      return self.depCache[inputFilepath]

    print("Collecting dependencies for {0}".format(inputFilepath), file=self.log)
    inputFiledir, _ = os.path.split(inputFilepath)
    deps = [inputFilepath]
    tree = ET.parse(inputFilepath)
    root = tree.getroot()

    for image in root.iter(SCHEMA_SVG + "image"):
      depFilename = image.get(SCHEMA_XLINK + "href")
      depFilepath = os.path.normpath(os.path.join(inputFiledir, depFilename))
      deps.append(depFilepath)
      _, extension = os.path.splitext(depFilename)
      if extension == ".svg":
        deps += self.collectSVGDeps(depFilepath)

    self.depCache[inputFilepath] = deps
    return deps

  def emitSVGTarget(self, inputFilepath, outputFilepath=None, scalex2=True):
    """Emits a target that rasterizes an SVG file."""
    inputFiledir, inputFilename = os.path.split(inputFilepath)
    inputFilenameRoot, inputFilenameExtension = os.path.splitext(inputFilename)

    if not outputFilepath:
      outputFilename = inputFilenameRoot + ".png"
      outputFilepath = os.path.join(self.buildDir, outputFilename)
      outputFilepath2x = os.path.join(self.buildDir, inputFilenameRoot + "@2x.png")
    else:
      outputFilepathRoot, outputFilepathExtension = os.path.splitext(outputFilepath)
      outputFilepath2x = outputFilepathRoot + "@2x" + outputFilepathExtension
    deps = self.collectSVGDeps(inputFilepath)

    self.emitTargetHead(outputFilepath, deps=[inputFilepath] + deps)
    self.emitCommand(self.rasterizer.rasterizeCommand(
      inputFilepath, outputFilepath, 1
    ))
    if scalex2:
      self.emitCommand(self.rasterizer.rasterizeCommand(
        inputFilepath, outputFilepath2x, 2
      ))

    return outputFilepath

  def emitCopyCommand(self, fromFilepath, toFilepath):
    """Emits a command that copies a file."""
    if LINUX or DARWIN:
      self.emitCommand("cp {0} {1}".format(
        shellquote(fromFilepath), shellquote(toFilepath)
      ))
    elif WINDOWS:
      self.emitCommand("copy /Y {0} {1}".format(
        shellquote(fromFilepath), shellquote(toFilepath)
      ))

  def emitDeleteCommand(self, targetFilepath):
    """Emits a command that deletes a file."""
    if LINUX or DARWIN:
      self.emitCommand("rm -rf " + shellquote(targetFilepath))
    elif WINDOWS:
      self.emitCommand("del /S /Q " + shellquote(targetFilepath))

  def generate(self):
    """Walks the source directory and emits all found targets, including an 'all' and 'clean' target."""
    allDeps = []

    for dirname, subdirs, subfiles in os.walk(self.sourceDir):
      for inputFilename in subfiles:
        if inputFilename.startswith("_") \
          or any([i.startswith("_") for i in dirname.split(os.path.sep)]): continue
        _, extension = os.path.splitext(inputFilename)
        if extension != ".svg": continue
        inputFilepath = os.path.join(dirname, inputFilename)
        allDeps.append(
          self.emitSVGTarget(inputFilepath, scalex2=True)
        )

    # build/skin.ini:
    fromFilepath = os.path.join(self.sourceDir, "skin.ini")
    toFilepath = os.path.join(self.buildDir, "skin.ini")
    self.emitTargetHead(toFilepath)
    self.emitCopyCommand(fromFilepath, toFilepath)
    allDeps.append(toFilepath)
    # all:
    self.emitTargetHead("all", deps=allDeps, phony=True)
    # clean:
    self.emitTargetHead("clean", phony=True)
    for filename in allDeps:
      self.emitDeleteCommand(filename)
    self.emitDeleteCommand("preview.png")
    self.emitDeleteCommand("Kirei.osk")
    # preview.png:
    self.emitSVGTarget(
      os.path.join(self.sourceDir, "_preview.svg"),
      outputFilepath="preview.png", scalex2=False
    )
    # Kirei-MAJOR.MINOR.PATCH.osk:
    packagename = "Kirei-{0}.osk".format(self.skinVersion)
    self.emitTargetHead(packagename, deps=["all"])
    self.emitCommand("{0} -m zipfile -c Kirei.osk {1}".format(
      shellquote(sys.executable), " ".join([shellquote(i) for i in allDeps])
    ))
    # package:
    self.emitTargetHead("package", deps=[packagename], phony=True)
    # release:
    self.emitTargetHead("release", deps=["package", "preview.png"], phony=True)


if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(
    description="Generate a Makefile for building the Kirei osu! skin."
  )
  parser.add_argument("-o", "--output",
    type=argparse.FileType(mode="wt"),
    default="Makefile",
    help="output file, - for stdout (default: Makefile)"
  )
  parser.add_argument("-r", "--rasterizer",
    default="auto",
    help="the rasterizer to use (default: auto, search for one)"
  )
  parser.add_argument("--sourcedir",
    default="source",
    help="the directory of the source files, relative to the Makefile (default: source)"
  )
  parser.add_argument("--builddir",
    default="build",
    help="the output directory, relative to the Makefile (default: build)"
  )
  parser.add_argument("--rasterizer-path",
    default="",
    help="the path to the rasterizer executable, ignored if no rasterizer was passed (default: search)"
  )
  parser.add_argument("--list-rasterizers",
    action="store_true",
    help="search for and list all rasterizers and their paths and exit"
  )
  args = parser.parse_args()

  if args.list_rasterizers:
    for r in allRasterizers:
      rasterizer = r.find()
      if rasterizer:
        print("{} ({})".format(rasterizer.NAME, rasterizer.path))
    sys.exit(0)

  generator = Generator(args)
  generator.generate()
