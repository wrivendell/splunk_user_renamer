#!/usr/bin/env python3
##############################################################################################################
# Contact: Will Rivendell 
# 	E1: wrivendell@splunk.com
# 	E2: contact@willrivendell.com
##############################################################################################################

### Imports ###########################################
import threading, sys, os, re, pandas, shutil

from lib import wr_arguments as arguments
from lib import wr_logging as log
from lib import wr_common as wrc

###########################################
# Globals
########################################### 
# log files
wrc.clearConsole()
main_log = 'spur'
log_file = log.LogFile(main_log, remove_old_logs=True, log_level=arguments.args.log_level, log_retention_days=10, debug=arguments.args.debug_modules)

# start easy timer for the overall operation
spur_op_timer = wrc.timer('spur_timer', 600)
threading.Thread(target=spur_op_timer.start, name='spur_op_timer', args=(), daemon=False).start()

# normalize things
splunk_home = wrc.normalizePathOS(arguments.args.splunk_home)
splunk_user_folders_path = wrc.normalizePathOS(splunk_home + 'etc/users/')
if arguments.args.csv_folder:
	csv_path = wrc.normalizePathOS(arguments.args.csv_folder)
else:
	csv_path = ''

## master list of files and folders to be searched and modified
user_rename_dict = {} # main - used later

# Print Console Info
print("\n")
print("- SPUR(" + str(sys._getframe().f_lineno) +"): --- Splunk User Renamer: Starting ---- \n")
print("- SPUR(" + str(sys._getframe().f_lineno) +"): --- Splunk User Renamer: Timer Started ---- \n")
print("- SPUR(" + str(sys._getframe().f_lineno) +"): Main Log Created at: ./logs/" + (main_log) + " -")
log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): --- Splunk User Renamer: Starting ----"])
print("\n")
if arguments.args.test_run:
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): ########################################### -")
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): TEST RUN - No actual changes will be made!! -")
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): ########################################### -")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): TEST RUN - No actual changes will be made."])

########################################### ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Globals - END
###########################################

###########################################
# Functions - START
###########################################
def generateMasterFolderSearchList():
	# FOLDERS
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): Generating master search FOLDER list. These folders get backed up and renamed before any file contents are edited. -")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Generating master search FOLDER list. These folders get backed up and renamed before any file contents are edited."])
	user_folders_list = next(os.walk(splunk_user_folders_path))[1] # main - used later
	if not user_folders_list:
		print("- SPUR(" + str(sys._getframe().f_lineno) +"): No user folders found to rename. -")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): No user folders found to rename."])
	return(user_folders_list)

def generateMasterFileSearchList():
	# FILES
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): Generating master search FILE list. This is done AFTER user folders have been backed up and renamed. -")
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): This means usernames in the PATH to these files will be new, but the content is still previous usernames. -")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Generating master search FILE list. This is done AFTER USER FOLDERS have been backed up and renamed, which...."])
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"):  ...usernames in the PATH to files in USER FOLDERS will be new, but the CONTENT still has previous usernames, which is ok."])
	## full paths to the file names found
	master_file_list = arguments.args.file_names #  file names to look in for username matches to replace. Specified by user in args-> used to get full file paths
	master_file_path_list = []
	search_in = splunk_home, # trailing comma is to make this a single item tuple as the function requires
	for fn in master_file_list:
		found = wrc.findFileByName(fn, search_in, arguments.args.file_search_list, 
												arguments.args.file_search_list_type, 
												arguments.args.file_ignore_list, 
												arguments.args.file_ignore_list_type)
		if found[0]:
			for i in found[1]: # if full paths found add to master list
				master_file_path_list.append(i)
	if not master_file_path_list:
		print("- SPUR(" + str(sys._getframe().f_lineno) +"): No file names found to search in for users. -")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): No file names found to search in for users."])
	else:
		return(master_file_path_list)

def determineCSV():
	# process csv or rename params
	global user_rename_dict
	if not csv_path:
		prefix_or_suffix_specified = False
		uname_prefix = ''
		uname_suffix = ''
		if arguments.args.uname_prefix:
			uname_prefix = str(arguments.args.uname_prefix)
			prefix_or_suffix_specified = True
		if arguments.args.uname_suffix:
			uname_suffix = str(arguments.args.uname_suffix)
			prefix_or_suffix_specified = True
		if not prefix_or_suffix_specified:
			print("- SPUR(" + str(sys._getframe().f_lineno) +"): No CSV folder specified and no prefix or suffix specified, therefore nothing to do. Exiting. -")
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): No CSV folder specified and no prefix or suffix specified, therefore nothing to do. Exiting."])
			spur_op_timer.stop()
			sys.exit()
		else:
			print("- SPUR(" + str(sys._getframe().f_lineno) +"): No CSV specified, creating rename dict from prefix and suffix. -")
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): No CSV specified, creating rename dict from prefix and suffix."])
			for uname in user_folders_list:
				user_rename_dict[str(uname)]=uname_prefix + str(uname) + uname_suffix
	else:
		print("- SPUR(" + str(sys._getframe().f_lineno) +"): CSV Folder Specified, attempting to read. -")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): CSV Folder Specified, attempting to read."])
		try:
			csv_folder_filenames = os.listdir(csv_path) # main - used later
			if not csv_folder_filenames:
				raise
			csv_df_list = []
			for csv in csv_folder_filenames:
				df = pandas.read_csv(csv_path + csv, header=None, engine='python', na_values='wr_spur_empty2021')
				if arguments.args.csv_header:
					df = df.iloc[1:] # remove the header
				df = df[[int(arguments.args.csv_old_uname_col),int(arguments.args.csv_new_uname_col)]] # we only want the two columns we care about (old and new unames)
				csv_df_list.append(df)
			df_full = pandas.concat(csv_df_list, axis=0, ignore_index=True)
			df_full = df_full.applymap(str.strip) # remove starting and trailing whitespaces from df strings
			user_rename_dict = df_full.set_index(arguments.args.csv_old_uname_col)[int(arguments.args.csv_new_uname_col)].to_dict()
			print("- SPUR(" + str(sys._getframe().f_lineno) +"): Done. -")
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Done."])		
		except Exception as ex:
			print("- WRC(" + str(sys._getframe().f_lineno) + "): CSV Could not be read or processed. Exiting. -")
			print(ex)
			log_file.writeLinesToFile(["(" + str(sys._getframe().f_lineno) + "): CSV Could not be read or processed. Exiting."] )
			log_file.writeLinesToFile(["(" + str(sys._getframe().f_lineno) + "): " + str(ex)] )
			spur_op_timer.stop()
			sys.exit()

def emailForUsernameCheck():
	# do a quick check to make sure the user didnt provide emaill addresses instead of usernames when users aren't email addresses or vice versa
	email_regex = '^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]{2,}$' # used to check if usernames in csv match usernames in splunk when one may be email address and one may not be
	for u in user_folders_list:
		orig_u_email_format = False
		if(re.search(email_regex, str(u))):
			orig_u_email_format = True
		for k, v in user_rename_dict.items():
			if not str(u) == str(k): # if uname doesnt match new uname
				if orig_u_email_format: # but original was an email address
					if not re.search(email_regex, str(k)): # provided original was not an email address
						new_k = str(k) + '@' + str(u.split('@')[1]) # add the email domain from the found splunk user to the provided original username and see if it matches now
					if str(u) == str(k): # if they match now, add the modified uname to the list instead
						print("- SPUR(" + str(sys._getframe().f_lineno) +"): Original: " + str(u) + " but non-email username: " + str(k) + " specified for replacement. Using email version.")
						log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Original: " + str(u) + " but non-email username: " + str(k) + " specified for replacement. Using email version."])
						user_rename_dict[new_k] = user_rename_dict.pop(k)
				else:
					if re.search(email_regex, str(k)): # if splunk user doesnt have email address, strip it from the provided original which does and see if matches now
						new_k = k.split('@')[0]
					if str(u) == str(k): # if they match now, add the modified uname to the list instead
						print("- SPUR(" + str(sys._getframe().f_lineno) +"): Original: " + str(u) + " but email username: " + str(k) + " specified for replacement. Using non-email version.")
						log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Original: " + str(u) + " but email username: " + str(k) + " specified for replacement. Using non-email version."])
						user_rename_dict[new_k] = user_rename_dict.pop(k)

def renameUsersInFiles():
	'''
	Renames all found usernames in specified files
	Returns a dict of modifications
	'''
	## pre-flight reporting
	print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): The following files are being searched in for user renames. -")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): The following files are being searched in for user renames."])
	file_failed_renames = []
	file_changes_dict = {} # store all file changes here: file_name : {k orig : v new}
	for f in master_file_path_list:
		print("- SPUR(" + str(sys._getframe().f_lineno) +"):  - " + f + " -")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): 	- " + f])
	for f in master_file_path_list:
		tmp_changes_dict = {}
		tmp_changes_dict = wrc.replaceTextInFile(f, user_rename_dict, create_backup=True, backup_to=arguments.args.backup_folder, additional_starts_with=arguments.args.replace_starts_with, additional_ends_with=arguments.args.replace_ends_with, test_run=arguments.args.test_run, verbose_prints=True)
		if tmp_changes_dict == "FAILED":
			file_failed_renames.append(f)
		elif tmp_changes_dict:
			file_changes_dict[f] = tmp_changes_dict
		else:
			continue
	if not arguments.args.test_run:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): All specified file modifications complete, successfuls will have a backup at: " + arguments.args.backup_folder + " -")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): All specified file modifications complete, successfuls will have a backup at: " + arguments.args.backup_folder])
	else:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): TEST RUN COMPLETE - NO CHANGES WERE MADE - Scroll up or check logs for details of what would have changed -")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): TEST RUN COMPLETE - NO CHANGES WERE MADE - Scroll up to see details on what would have changed"])
	return(file_changes_dict, file_failed_renames)

def renameUserFolders():
	'''
	Renames all found folders matching usernames
	Returns a dict of modifications
	'''
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): Starting rename of user folders. -\n")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Starting rename of user folders.\n"])
	folder_changes_dict = {} # store all folder changes here: {k orig : v new}
	user_folder_failed_renames = []
	user_folders_not_in_list = []
	for u in user_folders_list:
		found = False
		for k, v in user_rename_dict.items():
			if str(u) == str(k):
				found = True
				if os.path.exists(splunk_user_folders_path + str(v)):
					if arguments.args.test_run:
						print("- SPUR(" + str(sys._getframe().f_lineno) +"): TEST MODE - New User Folder Already exists! Script would back it up and then delete it: " + splunk_user_folders_path + str(v))
						log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): TEST MODE - New User Folder Already exists! Script would back it up and then delete it: " + splunk_user_folders_path + str(v)])
					else:
						try:
							print("- SPUR(" + str(sys._getframe().f_lineno) +"): New User Folder Already exists! Backing it up and then deleting it first: " + splunk_user_folders_path + str(v))
							log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): New User Folder Already exists! Backing it up and then deleting it first: " + splunk_user_folders_path + str(v)])
							tmp_backup_path = wrc.normalizePathOS(arguments.args.backup_folder)[:-1] + splunk_user_folders_path + str(v)
							counter = 0
							while os.path.exists(tmp_backup_path):
								counter += 1
								tmp_backup_path = wrc.normalizePathOS(arguments.args.backup_folder)[:-1] + splunk_user_folders_path + str(v) + "_" + str(counter)
							shutil.copytree(splunk_user_folders_path + str(v), tmp_backup_path)
							shutil.rmtree(splunk_user_folders_path + str(v))
						except Exception as ex:
							print("- SPUR(" + str(sys._getframe().f_lineno) +"): Exiting, as had issue backing up or deleting: " + splunk_user_folders_path + str(v))
							print("- SPUR(" + str(sys._getframe().f_lineno) +"): Issue: " + str(ex))
							log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Exiting, as had issue backing up or deleting: " + splunk_user_folders_path + str(v)])
							log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Issue: " + str(ex)])
							spur_op_timer.stop()
							sys.exit()
				if wrc.renameFolder(splunk_user_folders_path + str(k), splunk_user_folders_path + str(v), create_backup=True, backup_to=arguments.args.backup_folder, test_run=arguments.args.test_run):
					print("- SPUR(" + str(sys._getframe().f_lineno) +"): Original: " + splunk_user_folders_path + str(k))
					print("- SPUR(" + str(sys._getframe().f_lineno) +"): Renamed To: " + splunk_user_folders_path + str(v))
					log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Original: " + splunk_user_folders_path + str(k)])
					log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Renamed To: " + splunk_user_folders_path + str(v)])
					folder_changes_dict[splunk_user_folders_path + str(k)] = splunk_user_folders_path + str(v)
					break
				else:
					user_folder_failed_renames.append(splunk_user_folders_path + str(k))
					break
		if not found:
			user_folders_not_in_list.append(str(u))
		
	print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): Rename complete, successfuls will have a backup at: " + arguments.args.backup_folder + " -\n")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): Rename complete, successfuls will have a backup at: " + arguments.args.backup_folder + "\n"])
	return(folder_changes_dict, user_folder_failed_renames, user_folders_not_in_list)

def finalReport(folder_changes_dict, user_folder_failed_renames, user_folders_not_in_list, file_changes_dict, file_failed_renames):
	# final report
	## folders
	if folder_changes_dict:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): The Following FOLDER Changes were detected: ")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): The Following FOLDER Changes were detected:"])
		for k, v in folder_changes_dict.items():
			print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): - Old Folder: " + str(k).strip())
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): - Old Folder: " + str(k).strip()])
			print("- SPUR(" + str(sys._getframe().f_lineno) +"): - TO  Folder: " + str(v))
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): - TO  Folder: " + str(v)])

	if user_folder_failed_renames:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): The following user folders failed to rename: -" )
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): The following user folders failed to rename:"])
		for i in user_folder_failed_renames:
			print("- SPUR(" + str(sys._getframe().f_lineno) +"):	" + i + " -" )
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"):		" + i])
	
	if user_folders_not_in_list:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): The following user folders were found but not in CSV so not touched: -" )
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): The following user folders were found but not in CSV so not touched:"])
		for uf in user_folders_not_in_list:
			print("- SPUR(" + str(sys._getframe().f_lineno) +"):	" + str(uf) + " -" )
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"):		" + str(uf)])

	## files
	if file_changes_dict:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): The Following File Changes were detected: ")
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): The Following File Changes were detected:"])
		for fn, line in file_changes_dict.items():
			print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): -FILENAME: " + fn )
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): -FILENAME: " + fn])
			for k, v in line.items():
				print("- SPUR(" + str(sys._getframe().f_lineno) +"): - Old Line: " + str(k).strip())
				log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): - Old Line: " + str(k).strip()])
				print("- SPUR(" + str(sys._getframe().f_lineno) +"): - TO  Line: " + str(v))
				log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): - TO  Line: " + str(v)])

	if file_failed_renames:
		print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): The following files failed to rename users in the content due to access or permissions: -" )
		log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): The following files failed to rename users in the content due to access or permissions:"])
		for i in file_failed_renames:
			print("- SPUR(" + str(sys._getframe().f_lineno) +"):	" + str(i) + " -" )
			log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"):		" + str(i)])


########################################### ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Functions - END
###########################################

###########################################
# Runtime >>>
###########################################
determineCSV()
user_folders_list = generateMasterFolderSearchList()

#email usernames check
emailForUsernameCheck()

# RENAMES START NOW
## start renaming user folders
if user_folders_list:
	folder_changes_dict, user_folder_failed_renames, user_folders_not_in_list = renameUserFolders()

## start replacing usernames in files
master_file_path_list = generateMasterFileSearchList()
if not master_file_path_list and not user_folders_list:
	print("- SPUR(" + str(sys._getframe().f_lineno) +"): No file names found to search in for users or folders to be renamed. Exiting. -")
	log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): No file names found to search in for users or folders to be renamed. Exiting."])
	spur_op_timer.stop()
	sys.exit()

if master_file_path_list:
	file_changes_dict, file_failed_renames = renameUsersInFiles()

## final report
finalReport(folder_changes_dict, user_folder_failed_renames, user_folders_not_in_list, file_changes_dict, file_failed_renames)

# outro
print("\n- SPUR(" + str(sys._getframe().f_lineno) +"): --- Splunk User Renamer: Completed ---- ")
print("- SPUR(" + str(sys._getframe().f_lineno) +"): --- Check wr_common (wrc) log for additional details. ---- \n")
log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): --- Splunk User Renamer: Completed ---- "])
log_file.writeLinesToFile(["SPUR(" + str(sys._getframe().f_lineno) +"): --- Check wr_common (wrc) log for additional details. ----"])

spur_op_timer.stop()
sys.exit()