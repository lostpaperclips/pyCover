# -*- coding: utf-8 -*-
import getopt, os, platform, subprocess, sys

version  = "0.0.4"
imageExt = [[".jpg", "image/jpeg"], [".png", "image/png"], [".gif", "image/gif"]]
USE_MUTAGEN = "false"
USE_FIRST_IMAGE_FOUND = "false"
MUTAGEN_MODULE = ""
CMD_CONVERT = "convert"
CMD_EYED3 = "eyeD3"
CMD_ID3 = "id3v2"
DEBUG_FLAG = "false"
DEFAULT_RESOLUTION = "600x600"
coverJpg = "cover-embed-" + DEFAULT_RESOLUTION + ".jpg"
coverPng = "cover-embed-" + DEFAULT_RESOLUTION + ".png"

#######################################################################
#
# Method called to walk the directory tree
#
# args: extension to find
# dirname: name of current directory
# list of files in the current directory
#
def find(arg, dirname, names):
  foundMp3 = "false"
  for item in names:
    pathname = os.path.join(dirname, item)
    pathname = os.path.normpath(pathname)
    fileExtension = os.path.splitext( item )
    if os.path.isfile(pathname) and fileExtension[1].lower() == arg:
      debug("Found " + arg + " in " + dirname)
      foundMp3 = "true"
      break

  if foundMp3 == "false":
    debug("No "+ arg +"s found in directory " + dirname)
    return

  # (1) Get an image to embed
  fullCoverJpg = findImage(dirname, names)

  if fullCoverJpg is None or len(fullCoverJpg) == 0:
    debug("No acceptable image found for " + dirname)
    return;
  
  # 2) Loop through contents and determine
  # if it is a file or a directory. Directories
  # can be skipped. Whereas for files, we'll
  # want to make a callback to embed the images.
  badAudioFiles = []
  for item in names:
    pathname = os.getcwd()
    pathname = os.path.join(pathname, dirname)
    pathname = os.path.join(pathname, item)
    pathname = os.path.normpath(pathname)
    if os.path.isfile(pathname) and pathname.lower().find(arg)>0:
      embedReturnCode = embedImage(pathname, fullCoverJpg)
      if 0 < embedReturnCode:
        badAudioFiles.append(pathname)
  if 0 < len(badAudioFiles):
    print "Errors occurred embedding images in the following files:"
    sys.stdout.write(" * ")
    print "\n\r * ".join(badAudioFiles)

#######################################################################
#
# Given a directory, attempt to find a suitable cover image
#
def findImage(directory, filenames):
  imageFileToUse = ""
  # 1) Look in directory for if there is an
  # album cover, leave if not
  if coverJpg in filenames:
    debug("Found JPEG cover image, no conversion necessary")
    fullCoverJpg = os.path.join(directory, coverJpg)
    fullCoverJpg = os.path.normpath(fullCoverJpg)
    imageFileToUse = [fullCoverJpg, "image/jpeg"]
  elif coverPng in filenames:
    # No JPEG image found, but a legally named PNG exists
    imageFileToUse = convertImage(directory, coverPng, coverJpg)
  else:
    desiredImage = guessImageFile(directory, filenames);
    # found an acceptable image (based on extension)
    # if it is already a JPG, just make a copy. Otherwise do a
    # do a conversion
    if desiredImage == "":
      print >> sys.stderr, "no image found in " + directory
    elif USE_FIRST_IMAGE_FOUND == "true":
      imageFileToUse = desiredImage
    elif len(desiredImage[0]) > 0:
      imageFileToUse = convertImage(directory, desiredImage[0], coverJpg)
    # by virtue of making it out of the loop, we have admitted that
    # no acceptable image was present.
  return imageFileToUse;

#######################################################################
#
# Simple heuristic for determining the correct cover art file.
#
def guessImageFile(directory, filenames):
  # There is no well-defined image for this directory.
  # Attempt to guestimate a reasonable replacement.  Look
  # through what is available & sort those 
  potentialImages = []
  for aFile in filenames:
    for extension,mime in imageExt:
      fileExtension = os.path.splitext( aFile )
      if fileExtension[1].lower() ==  extension:
	debug("Looking at using file: " + aFile + " | Mime Type: " + mime)
	fullpath = os.getcwd()
        fullpath = os.path.join(fullpath, directory)
        fullpath = os.path.join(fullpath, aFile)
        fullpath = os.path.normpath(fullpath)
        potentialImages.append([fullpath, mime])
      
  desiredImage = ""
  for currentFile, currentMime in potentialImages:
    if len(desiredImage) > 0:
      break;
    goodKeywords = [ "front", "large", "big"]
    for keyword in goodKeywords:
      if currentFile.lower().find(keyword) > 0:
        desiredImage = [currentFile, currentMime]
        debug("found image: " + currentFile)
        break;
	
  # The first heuristic did not work, just pick the first image
  if desiredImage is None or desiredImage == "":
    if len(potentialImages) > 0:
      debug("No image found, defaulting to " + potentialImages[0][0])
      desiredImage = potentialImages[0];

  return desiredImage

#######################################################################
#
# Linux command-line approach for converting/shrinking an image file.
#
# directory: directory where the file lives
# foundImage: fullpath to the the desired image
# desiredFilename: name of the output file
#
def convertImage(directory, foundImage, desiredFilename):
  # With imagemagick version 6.4.8.3, the command
  # to convert the image is similar to:
  # convert cover.png -geometry 600x600 cover.jpg
  fullCoverJpg = os.path.join(directory, desiredFilename)
  fullCoverJpg = os.path.normpath(fullCoverJpg)
  cmd = [CMD_CONVERT, foundImage, "-geometry", DEFAULT_RESOLUTION , fullCoverJpg]
  shellCommandWrapper(cmd)
  return [fullCoverJpg, "image/jpeg"]

#######################################################################
#
# Wrapper function to pick the correct means of embedding the 
# album artwork into the audio file.
#
def embedImage(audiofile, image):
  addReturnCode = 0
  
  if USE_MUTAGEN:
    addReturnCode = embedImageViaMutagen(audiofile, image)
  else:
    addReturnCode = embedImageViaLinuxCommandLine(audiofile, image)

  return addReturnCode

#######################################################################
#
# Use the "v2" approach of Mutagen
#
def embedImageViaMutagen(audiofile, image):
  returnCode = 0
  exec "from mutagen.mp3 import MP3"
  exec "from mutagen.id3 import ID3, APIC, error"
  audioTags = ID3(audiofile)
  try:
    debug("Adding " + image[0] + " to the file " + audiofile )
    audioTags.add(APIC(encoding=3, mime=image[1], type=3, desc=u'Cover',data=open(image[0]).read()))
    audioTags.save()
  except error:
    returnCode = 1

  return returnCode

#######################################################################
#
# Use the "v1" approach of several command-line tools
#
def embedImageViaLinuxCommandLine(audiofile, image):
  removeReturnCode = 0
  addReturnCode = 0
  removeReturnCode  += zeroBpm(audiofile);

  # (1) Remove all existing images
  removeReturnCode += removeOtherImage(audiofile);
  removeReturnCode += removeOtherImage(audiofile);
  removeReturnCode += removeFrontImage(audiofile);
  removeReturnCode += removeFrontImage(audiofile);

  # (2) remove cruft
  removeReturnCode += removeCruft(audiofile);

  # (3) check if valid ID3 tag
  removeReturnCode += checkValidId3Tag(audiofile);

  # (4) add front image
  addReturnCode += addFrontImage(audiofile, image[0]);
  
  if 0 < removeReturnCode:
    debug("--------------------------------------------------------------------")
    debug("Errors occured when removing/cleaning ID3 tag for: ")
    debug(audiofile)
    debug("This behavior is unexpected, but may not impact embedding the image.")
    debug("--------------------------------------------------------------------")
    
  if 0 < addReturnCode:
    debug("--------------------------------------------------------------------")
    debug("The unable to embed image in: ")
    debug(audiofile)
    debug("--------------------------------------------------------------------")
  
  return addReturnCode

#######################################################################
#
# Linux command-line wrapper for adding the front cover artwork
#
def addFrontImage(theFile, imageFile):
  imagePathArg = "--add-image=" + imageFile + ":FRONT_COVER" 
  cmd = [CMD_EYED3, "--no-color", imagePathArg, theFile]
  return shellCommandWrapper(cmd)

#######################################################################
#
# Linux command-line wrapper for converting to the right ID3 version
#
def checkValidId3Tag(theFile):
  cmd = [CMD_EYED3, "--no-color", "--to-v2.4", theFile]
  return shellCommandWrapper(cmd)

#######################################################################
#
# Linux command-line wrapper hack for dealing with floating-point BPMs
#
def zeroBpm(theFile):
  cmd = [CMD_EYED3, "--bpm=90", theFile]
  return shellCommandWrapper(cmd)

#######################################################################
#
# Linux command-line wrapper for removing the front cover artwork
#
def removeFrontImage(theFile):
  cmd = [CMD_EYED3, "--no-color", "--add-image=:FRONT_COVER", theFile]
  return shellCommandWrapper(cmd)

#######################################################################
#
# Linux command-line wrapper for removing the other artwork
#
def removeOtherImage(theFile):
  cmd = [CMD_EYED3, "--no-color", "--add-image=:OTHER", theFile]
  return shellCommandWrapper(cmd)

#######################################################################
#
# Linux command-line wrapper for removing cruft
#  * Mainly needed for older ID3 editors, may no longer be an issue
#    on newer (2010+) installs
#
def removeCruft(theFile):
  cmd = [CMD_ID3, "-APIC", "", theFile]
  return shellCommandWrapper(cmd)

#######################################################################
#
# Simple environment sanity check
#
def checkEnvironment():
  #
  # try to dynamically load mutagen
  #
  try:
    global MUTAGEN_MODULE 
    MUTAGEN_MODULE = __import__("mutagen")
    debug(MUTAGEN_MODULE)
    USE_MUTAGEN = "true"
    debug("Able to dynamically load mutagen")
  except:
    debug("Unable to dynamically load mutagen")
    if "Linux" <> platform.system():
      print >> sys.stderr, "*********************************************************"
      print >> sys.stderr, "***            Environment Check Failed!              ***"
      print >> sys.stderr, "***                                                   ***"
      print >> sys.stderr, "               mutagen must be installed"
      print >> sys.stderr, "***                                                   ***"
      print >> sys.stderr, "            http://code.google.com/p/mutagen/"
      print >> sys.stderr, "***                                                   ***"
      print >> sys.stderr, "*********************************************************"
      print
      sys.exit(1)
    #
    # fallback 'raw' method, look for the appropriate command-line utilities
    #
    checkEnvironmentHelper([CMD_EYED3, "--help"])
    checkEnvironmentHelper([CMD_ID3])
  if "Linux" == platform.system():
    checkEnvironmentHelper([CMD_CONVERT])
  else:
    global USE_FIRST_IMAGE_FOUND
    USE_FIRST_IMAGE_FOUND = "true"
  
#######################################################################
#
# Helper method for displaying errors about some simple command-line
# environment checks (for Linux)
#
def checkEnvironmentHelper(command):  
  if 0 < shellCommandWrapper(command):
    print >> sys.stderr, "*********************************************************"
    print >> sys.stderr, "***            Environment Check Failed!              ***"
    print >> sys.stderr, " Unable to locate '" + command[0] + "' in the PATH"
    print >> sys.stderr, "*********************************************************"
    print
 
#######################################################################
#
# Prints debugging messages (if the debugging flag has been set)
#
def debug(message):
  if DEBUG_FLAG == "true":
    print message

#######################################################################
#
# Small wrapper method for executing Linux Shell Commands
#
def shellCommandWrapper(command):
  FNULL = open(os.devnull, 'w')
  process = subprocess.Popen(command, shell=False, bufsize=1, \
            stdin=None, stdout=FNULL, stderr=FNULL)
  process.wait()
  return process.returncode
  
#######################################################################
#
# Print Usage Information
#
def usage():
  print
  print "This script takes one or more arguments that are expected to be a "     + \
        "a single directory or set of directories. For each argument supplied, " + \
        "the script will recurse into the directory and look for an image file. If a " + \
        "file is found, it will be converted to the default resolution (" + DEFAULT_RESOLUTION + \
        "). The script will then look for any MP3s in the directory. If found, the " + \
        "image will be embedded into each file (overwriting an existing embedded image)."

#######################################################################
#
#
# Start of the 'main()' function
# 
def main():
  #######################################################################
  #
  # Read Command-Line
  #
  try:
    opts, args = getopt.getopt(sys.argv[1:], "hd", ["help", "debug", \
                               "use-first-image", "use-mutagen"])
  except getopt.GetoptError, err:
    # print help information and exit:
    print >> sys.stderr, err
    usage()
    sys.exit(2)
  #######################################################################
  #
  # Parse Command-Line Options and Arguments
  # 
  for o, a in opts:
    if o in ("-h", "--help"):
      usage()
      sys.exit()
    elif o in ("-d", "--debug"):
      global DEBUG_FLAG
      DEBUG_FLAG = "true"
    elif o == "--use-first-image":
      global USE_FIRST_IMAGE_FOUND
      USE_FIRST_IMAGE_FOUND = "true"
    elif o == "--use-mutagen":
      global USE_MUTAGEN
      USE_MUTAGEN = "true"
    else:
      assert False, "unhandled option"
  #######################################################################
  #
  # Now that all the processing is out of the way, walk the directory
  # structure and embed artwork into any discovered MP3 files.
  #
  if len(args) == 0:
    print >> sys.stderr, "Missing command-line arguments"
    usage()
  else:
    checkEnvironment()
    for directory in args:
      os.path.walk(directory, find, ".mp3")

if __name__ == "__main__":
    main()
