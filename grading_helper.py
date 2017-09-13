import zipfile
import argparse
import subprocess
import threading
import tempfile
import shutil
import time
import os

class bcolors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    ORANGE = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def unzipFile(f, extract_dir):
    #Unzip
    print(bcolors.BLUE + "Extracted to %s" % extract_dir + bcolors.ENDC)
    zip_ref = zipfile.ZipFile(f, 'r')
    zip_ref.extractall(extract_dir)
    zip_ref.close()

def runFile(f):
    fp = open(f, "r")
    lines = fp.readlines()[:10]
    fp.close()
    for line in lines:
        if line.strip().startswith("#"):
            print(line.rstrip())
    subprocess.call("python %s" % f, shell=True)

def replace(file_path, pattern, subst):
    fh, abs_path = tempfile.mkstemp()
    with os.fdopen(fh, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    os.remove(file_path)
    shutil.move(abs_path, file_path)

def add_grade(extract_dir, grade):
    grade_file = "grades.txt"
    studentName = extract_dir.split('/')[1]
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
    cwd = os.getcwd()

    for (dirpath, dirnames, filenames) in os.walk(extract_dir):
        for fi in filenames:
            fp = cwd + "/" + dirpath + "/" + fi
            if "MACOSX" not in fp:
                grading_files.append(fp)

    grading_files = sorted(grading_files)
    grading_files.insert(0, "grade")
    return grading_files

def printSelectionList(grading_files):
    print("[-] skip")
    for idx, fn in enumerate(grading_files):
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
            return None
    return selection

def getZipFilesFromDir(directory):
    print(directory)
    files = []
    if os.path.isdir(directory):
        for (dirpath, dirnames, filenames) in os.walk(directory):
            for f in filenames:
                if os.path.splitext(f)[1] == ".zip":
                    files.append(dirpath + f)
                else:
                    print("%s is not a zip!" % f)
    else:
        files.append(directory)
    return files

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    cwd = os.getcwd()
    grades_file = cwd + "/grades.txt"
    grading_dir = args.file
    if "/" not in grading_dir:
        grading_dir += "/"

    files = getZipFilesFromDir(grading_dir)
    #If arg passed in is directory, do all files in directory. Otherwise just do file given.
   
    curr_graded,skip_already_graded = getAlreadyGradedStudents(grades_file)
        
    for f in files:
        extract_dir = f.split('-')[0]
        studentName = extract_dir.split('/')[1]

        if skip_already_graded and (studentName in curr_graded):
            print("Skipping %s" % studentName)
            continue
      
        unzipFile(f, extract_dir)
        grading_files = getGradeableFiles(extract_dir)

        while(1):
            printSelectionList(grading_files)
            selection_number = input(bcolors.GREEN + "Enter a selection\n" + bcolors.ENDC)
            selection = parseSelection(grading_files, selection_number)
           
            if not selection:
                continue
            if selection == "skip":
                break
            elif selection == "grade":
                grade = str(input(bcolors.RED + "What grade does this peasant deserve?\n" + bcolors.ENDC))
                if add_grade(extract_dir, grade) == 0:
                    break
                else:
                    continue
            else:
                new_thread = threading.Thread(target=runFile(selection), args=())
                new_thread.start()

        shutil.rmtree(extract_dir)



if(__name__ == "__main__"):
    main()
