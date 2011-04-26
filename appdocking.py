#!/usr/bin/python

import os, sys
import plistlib
import subprocess
import getopt
import string

from random import randrange

debug = False
# pre-pend user folder to this dir
plist_default_loc = "Library/Preferences/com.apple.dock.plist"

# To define a pack, define a dict like so:
#	"<pack_name>" : [
# 		("<parent-folder1 path from '/Applications'>", "name of app1 without '.app'"),
# 		("<parent-folder2 path from '/Applications'>", "name of app2 without '.app'"),
# 	]
# Parent folder is <""> if parent folder _is_ /Applications -- see 'base_install'
# 
# To add a package to each dock call 'python dock.py --all --add <pack_name>'
# without the '<' and '>'
packs = {
	"cs5": [
		("Adobe Illustrator CS5","Adobe Illustrator"), # you tricky bastard!
		("Adobe Photoshop CS5","Adobe Photoshop CS5"),
		("Adobe InDesign CS5","Adobe InDesign CS5"),
	],
	"cs3": [ # 
		("Adobe Illustrator CS3","Adobe Illustrator"), # you tricky bastard!
		("Adobe Photoshop CS3","Adobe Photoshop CS3"),
		("Adobe InDesign CS3","Adobe InDesign CS3"),
	],
	"office": [
		("Microsoft Office 2008","Microsoft Entourage"),
	],
	"base_install": [ # mostly for removal of std. applications
		("","Front Row"),
		("","iCal"),
		("", "Mail")
	],
}

def isUnique(pl, guid):
	for section in ['persistent-apps', 'persistent-others']:
		for dock_item in pl[section]:
			try:
				this_GUID = dock_item['GUID']
			except:
				this_GUID = None
			if this_GUID == guid:
				return False
	return True



def uniqueGUID(pl):
	"""loops thru items in the plist to ensure there isn't already a GUID in there that matches the generated GUID, returns False if the GUID is not unique"""
	guid = randrange(999999999)
	while not isUnique(pl,guid):
		guid = randrange(999999999)
	
	return guid

def unique_label(pl, path):
	for item in pl["persistent-apps"]:
		if item["tile-data"]["file-data"]["_CFURLString"] == path:
			print path
			return False
	return True

def convertPlist(path, format):
    if os.system('plutil -convert '+format+' '+path) != 0:
        print 'failed to convert plist', '"'+path+'"'
        sys.exit(1)

# only called when either addPackage or removePackage actually changes the dock
# - to: path to the dock-plist to write the changes into
# - tmp: the in-memory copy of the plist-file we have 
def commitChanges(pl, to, tmp):
	# pl = removeLongs(pl)
	plist_stat = os.stat(to)
	writePlist(pl, to)
	convertPlist(to, 'binary1')
	os.chown(to, plist_stat.st_uid, plist_stat.st_gid)
	os.chmod(to, plist_stat.st_mode)
	os.system('/usr/bin/killall -HUP Dock >/dev/null 2>&1')
	os.remove(tmp)
	if debug:
		if os.path.exists(tmp) == False:
			print "tmp-folder deleted"

def writePlist(pl, plist_path):
    """writes a plist object down to a file"""
    try:
        plistlib.writePlist(pl, plist_path)
    except AttributeError: # if there was an AttributeError, we may need to use the older method for writing the plist down
        try:
            plistlib.Plist.write(pl, plist_path)
        except:
            print 'failed to write plist'
            sys.exit(5)

def plistFromPath(plist_path):
    convertPlist(plist_path, 'xml1')
    return readPlist(plist_path)

def readPlist(plist_path):
	"""returns a plist object read from a file path"""
	try:
		pl = plistlib.plistFromPath(plist_path)
	except AttributeError: # there was an AttributeError, we may need to use the older method for reading the plist
		try:
			pl = plistlib.Plist.fromFile(plist_path)
		except:
			print 'failed to read plist'
			sys.exit(5)
	return pl

def getPlistDict(path):
	# plist_path = os.path.expanduser("~/Library/Preferences/com.apple.dock.plist")	
	tmp_path = "/tmp/com.edit_dock.tmp.plist"	
	subprocess.call(['cp', path, tmp_path])
	
	return plistFromPath(tmp_path), tmp_path

def usage(e=None):
	"""Displays usage information and error if one occurred"""
	name = os.path.basename(sys.argv[0])

	print "usage:     %s -h" % (name,)
	print "usage:     %s --add <package name>" % (name,)
    # print "usage:     %s --remove <dock item label> [ plist_location_specification ]" % (name,)
    # print "usage:     %s --move <dock item label>  position_options [ plist_location_specification ]" % (name,)
    # print "usage:     %s --find <dock item label> [ plist_location_specification ]" % (name,)
	if e != None:
		print ""
		print 'Error processing options:', e
	sys.exit(0)


def addPackage(pl, pack):
	# adding an application
	section = "persistent-apps" # or persistent-others for folder
	tile_type = "file-tile"
	applications = '/Applications'
	
	changed = False
	for folder, app in pack:
		label_name = app
		new_guid = uniqueGUID(pl)
		app_path = os.path.join(applications,folder,app + ".app")
		# if debug: print app_path
		
		if not unique_label(pl,app_path):
			print 'Already in dock: ', app_path
			continue
			
		if os.path.exists(app_path):
			new_item = {
				'GUID':new_guid,
				'tile-data': {
					'file-data': {
						'_CFURLString': app_path,
						'_CFURLStringType': 0,
					},
					'file-label':label_name,
					'file-type':32
				},
				'tile-type':tile_type,
			}
			# place icon at beginning in array:
			print 'Added app: ', app
			pl[section].insert(0, new_item )
			changed = True
		else:
			# ignore error but print what didn't work
			print "app '",app_path,"' does not exist"

	return changed

def removeItem(pl, item_name):
	for dock_item in pl['persistent-apps']:
		if dock_item['tile-data']['file-label'] == item_name:
			pl['persistent-apps'].remove(dock_item)
			print 'removed app: ', item_name
			return True
	for dock_item in pl['persistent-others']:
		if dock_item['tile-data']['file-label'] == item_name:
			print 'removed app:', item_name
			pl['persistent-others'].remove(dock_item)
			return True
	return False

#
# Remove Icons from the dock
# - pl: removes a list of 
#
#
def removePackage(pl, pack):
	section = "persistent-apps" # or persistent-others for folder
	tile_type = "file-tile"
	changed = False
	for label in pack:
		if removeItem(pl, label):
			changed = True
	return changed

def listIcons(pl):
	for item in pl["persistent-apps"]:
		print "\t",item["tile-data"]["file-label"]
	
# add icons to a single dock.. to be extended to all users.
def main():
	try:
		(optargs, args) = getopt.getopt(sys.argv[1:], 
			'h', 
			['all', 'list', 'add=', 'del='])
	except getopt.GetoptError, err:
		# print help information and exit:
		print str(err) # will print something like "option -a not recognized"
		usage()
		sys.exit(2)
	
	all_users = False
	add = False
	add_pack = []
	remove = False
	del_pack = []
	pack = None
	list = False
	
	# Parse arguments
	for opt, arg in optargs:
		if opt in ("-h", "--help"):
			usage()
		elif opt == "--all":
			all_users = True
		elif opt == "--list":
			list = True
		elif opt == "--del":
			for arg in arg.lower().split(','):
				if arg in packs:
					del_pack.extend([label for dir, label in packs[arg]])
					remove = True
				else:
					print "--del '%s' not recognized. Valid packs are:" % (arg)
					for k in packs.keys():
						print "\t", k
						sys.exit(2)
		elif opt == "--add":
			for arg in arg.lower().split(','):
				if arg in packs:
					add_pack.extend(packs[arg])
					add = True
				else:
					print "--add '%s' not recognized. Valid packs are:" % (arg)
					for k in packs.keys():
						print "\t", k
						sys.exit(2)
	
	# Compile list of plist-files for all users..
	plist_paths = []
	if all_users:
		home_dirs = os.listdir( '/Users' )
		for usr in home_dirs:
			full_path = os.path.join('/Users',usr,plist_default_loc)
			if os.path.exists(full_path):
				print "Valid path: ", full_path
				plist_paths.append( full_path )
			else:
				# print "Invalid path", full_path
				continue
	else:
		plist_paths = [
			os.path.expanduser('~/Library/Preferences/com.apple.dock.plist')
		]

	# make changes to each dock!
	for plist_file in plist_paths:
		pl, tmp_path = getPlistDict(plist_file) # get plist file
		dirty = False # to make sure we only commit if we altered the dock
		if list:
			print "plist_file: ", plist_file, "icons: "
			listIcons(pl)
		if add:
			if addPackage(pl, add_pack): # returns true if we altered the dock
				dirty = True
		if remove:
			if removePackage(pl, del_pack):
				dirty = True
		
		if dirty: # if we changed anything => commit changes!
			commitChanges(pl, plist_file, tmp_path)
	
if __name__ == "__main__":
	main()