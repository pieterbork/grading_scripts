import patoolib
import argparse
import subprocess
import random
import threading
import tempfile
import shutil
import testhw1
import time
import os
import re

class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

#Uses patoolib to extract files from archive. p7zip, unzip, unrar dependent.
def unpackFile(f, extract_dir):
    if f.endswith(".rar"):
        os.makedirs(extract_dir)
    test = patoolib.extract_archive(f, outdir=extract_dir, verbosity=-1)
    print(bcolors.BLUE + "Extracted to %s" % extract_dir + bcolors.ENDC)

def output_reader(proc):
    for line in iter(proc.stdout.readline, b''):
        v = bytes(str(random.randint(1, 20)) + "\n", 'utf-8')
        l = line.decode('utf-8').lower()
        if 'higher' in l:
            proc.stdin.write(b'3\n')
            proc.stdin.flush()
        else:
            proc.stdin.write(v)
            proc.stdin.flush()
        print(l)

def runFile(f):
    fp = open(f, "r")
    lines = fp.readlines()[:10]
    fp.close()
    for line in lines:
        if line.strip().startswith("#"):
            print(line.rstrip())

    p = subprocess.Popen(['/usr/bin/python', f,'-i'], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE)

    
#    t = threading.Thread(target=output_reader, args=(p,))
#    t.start()

    r = random.randint(1,20)
    p.stdin.write(b'5\n')
    p.stdin.flush()

    

def replace(file_path, pattern, subst):
    fh, abs_path = tempfile.mkstemp()
    with os.fdopen(fh, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    os.remove(file_path)
    shutil.move(abs_path, file_path)

def addGrade(studentFolder, grade):
    grade_file = "grades.txt"
    studentName = studentFolder.split('-')[0]
    write_line = "%s %s\n" % (studentName, grade)
    yes = ['y', 'Y', 'yes']
    
    try:
        gf = open(grade_file, "r")
    except:
        gf = open(grade_file, "w")
        gf.close()
        gf = open(grade_file, "r")
    curr_content = gf.readlines()
    gf.close()
    found = False
    for line in curr_content:
        if studentName in line:
            ow = input("Found entry for %s, overwrite? (y/n/c)" % line)
            if ow in yes:
                found=True
                replace("grades.txt", line, write_line)
                return 0
            elif ow == "c":
                return 1
            else:
                found=True
                return 0
        
    if not found :
        gf = open(grade_file, "a")
        gf.write(write_line)
        gf.close()
        return 0

def getAlreadyGradedStudents(grades_file):
    curr_graded = []
    skip_already_graded=False
    yes = ['y', 'Y', 'yes']
    if os.path.isfile(grades_file):
        skip_graded = input(bcolors.RED + "A grade file was already found, would you like to skip already graded files?\n" + bcolors.ENDC)
        if skip_graded in yes:
            skip_already_graded = True
            fp = open(grades_file, "r")
            curr_graded = list(map(lambda x: x.split(' ')[0], fp.readlines()))
            fp.close()
    return curr_graded, skip_already_graded


def getGradeableFiles(extract_dir):
    grading_files = []
    for (dirpath, dirnames, filenames) in os.walk(extract_dir):
        for fi in filenames:
            grading_files.append(dirpath + "/" + fi)

    grading_files = sorted(grading_files)
    grading_files.insert(0, "grade")
    return grading_files

def printSelectionList(grading_files):
    print("[-] skip")
    for idx, fn in enumerate(grading_files):
        if "/" in fn:
            parts = fn.split("/")
            fn = parts[-2] + "/" + parts[-1]
        print("[%s] %s" % (idx, fn))

def parseSelection(grading_files, selection_number):
    if selection_number == "-":
        selection = "skip"
    else:
        try:
            selection_number = int(selection_number)
            selection = grading_files[selection_number]
        except:
            print("Out of range")
            selection = None
    return selection


#Creates a temporary directory and extracts or copies files.
def formatGradingDirectory(grading_file):
    ts = str(time.time())
    grading_dir = "grading_dir_" + ts + "/"
    if os.path.isfile(grading_file):
        file_ext = os.path.splitext(grading_file)[1]
        #1. Zip file straight from D2L
        if file_ext == ".zip":
            unpackFile(grading_file, grading_dir)
        #2. Not supported
        else:
            print("[%s] - Unsupported filetype." % file_ext)
            quit()
    else:
        #3. Directory full of python files
        if folderIsGradeable(grading_file):
            folderName = grading_dir + grading_file.rstrip('/').split('/')[-1]
            os.makedirs(grading_dir)
            shutil.copytree(grading_file, folderName)
            print(bcolors.BLUE + "Copied to %s" % (folderName) + bcolors.ENDC)
        #4. Directory full of zips/folders
        else:
            print("COPYTRRRREEEE")
            shutil.copytree(grading_file, grading_dir)
    return grading_dir

#Returns True if folder has python, also removes __MACOSX folder.
def folderIsGradeable(folder):
    folderHasPython = False
    for item in os.listdir(folder):
        item_path = "%s/%s" % (folder, item)
        if os.path.isfile(item_path):
            fi_ext = os.path.splitext(item)[1]
            if fi_ext == ".py":
                folderHasPython = True
        else:
            if item_path.endswith("__MACOSX"):
                shutil.rmtree(item_path)
                continue
            folderHasPython = folderIsGradeable(item_path)
    return folderHasPython

#Renames and extracts student archive to new folder
def extractStudentArchive(archive, grading_dir, gradeableFolders):
    archive_path = grading_dir + archive
    parts = archive.split(' - ')
    try:
        studentName = parts[1].split(' ')
        studentFileName = parts[3].split('.')[0]
        gradeableFolderName = grading_dir + studentName[1] + studentName[0] + "-" + studentFileName
    except:
        gradeableFolderName = archive_path
    unpackFile(archive_path, gradeableFolderName)
    os.remove(archive_path)
    if folderIsGradeable(gradeableFolderName):
        gradeableFolders.append(gradeableFolderName)
    else:
        print("%s not gradeable, removing directory!" % gradeableFolderName)
        shutil.rmtree(gradeableFolderName)

#Walks through folders/files in grading directory to unzip and/or see if they are gradeable. 
def getGradeableFolders(grading_dir):
    gradeableFolders = []
    archive_types = ['.rar', '.zip', '.7z']
    for (dirpath, dirnames, filenames) in os.walk(grading_dir):
        for di in dirnames:
            di_path = grading_dir + di
            if folderIsGradeable(di_path):
                gradeableFolders += di_path

        for fi in filenames:
            fi_path = grading_dir + fi
            fi_parts = os.path.splitext(fi)
            if fi_parts[1] in archive_types:
                studentArchive = re.match("^\d{3,6}-\d{3,6} - \w+ \w+.*", fi) or True
                if studentArchive:
                    extractStudentArchive(fi, grading_dir, gradeableFolders)

    return gradeableFolders

def handleSelection(selection, studentFolder):
    if selection == "skip":
        return 0
    elif selection == "grade":
        grade = str(input(bcolors.RED + "What grade does this peasant deserve?\n" + bcolors.ENDC))
        if addGrade(studentFolder, grade) == 0:
            return 0
    else:
        runFile(selection)
        #new_thread = threading.Thread(target=runFile(selection), args=())
        #new_thread.start()

def printStudentInformation(studentFolder, studentName):
    print(bcolors.GREEN + "\n%s" % studentName + bcolors.ENDC)
    folderParts = studentFolder.split('-')
    nameParts = re.findall('[A-Z][^A-Z]*', studentName)
    studentShortName = nameParts[1].lower()[0] + nameParts[0].lower() + "-hw1"
    try:
        folderSubmitted = folderParts[1].lower() + "-" + folderParts[2].lower()
        correctSubmission = (studentShortName == folderSubmitted)
        if correctSubmission:
            print(bcolors.BLUE + "Submitted folder in the correct format" + bcolors.ENDC)
        else:
            print(bcolors.ORANGE + "Wrong folder format %s should be %s" % (folderSubmitted, studentShortName) + bcolors.ENDC)
    except:
        print(bcolors.ORANGE + "Wrong folder format %s should be %s" % folderParts, studentShortName + bcolors.ENDC)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    cwd = os.getcwd()
    grades_file = cwd + "/grades.txt"
    
    grading_dir = formatGradingDirectory(args.file)
    gradeable_folders = getGradeableFolders(grading_dir)
    curr_graded, skip_already_graded = getAlreadyGradedStudents(grades_file)

    for folder in gradeable_folders:
        studentFolder = folder.split('/')[1]
        studentName = studentFolder.split('-')[0]
        if studentName in curr_graded and skip_already_graded:
            print(bcolors.BLUE + "Skipping %s" % studentName + bcolors.ENDC)
            continue
        else:
            printStudentInformation(studentFolder, studentName)
        grading_files = getGradeableFiles(folder)
        while(1):
            printSelectionList(grading_files)
            selection_number = input(bcolors.GREEN + "Enter a selection\n" + bcolors.ENDC)
            selection = parseSelection(grading_files, selection_number)
            status = handleSelection(selection, studentFolder, args.tests)
            if status == 0: 
                break
            else:
                continue
        shutil.rmtree(folder)
    shutil.rmtree(grading_dir)

if(__name__ == "__main__"):
    main()
