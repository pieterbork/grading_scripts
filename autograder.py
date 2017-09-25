from difflib import SequenceMatcher
import argparse
import patoolib
import threading
import subprocess
import shutil
import re
import os


archive_types = ['.rar', '.zip', '.7z']
grades_file = "grades.csv"
grading_dir = "grading_dir/"

class Student:
    def __init__(self, name, folder, archive_path, extract_path):
        self.name = name
        self.folder = folder
        self.archive_path = archive_path
        self.extract_path = extract_path
        self.grade = ""
        self.comments = ""

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
def unpack_file(f, extract_dir):
    if f.endswith(".rar"):
        os.makedirs(extract_dir)
    test = patoolib.extract_archive(f, outdir=extract_dir, verbosity=-1)
    print(bcolors.BLUE + "Extracted %s to %s" % (f, extract_dir) + bcolors.ENDC)

def create_student(archive):
    global grading_dir
    archive_parts = archive.split(' - ')
    name_parts = archive_parts[1].split(' ')
    student_name = name_parts[-1] + name_parts[0]
    student_folder = archive_parts[3].split('.')[0]
    student_archive = grading_dir + archive
    student_extract = grading_dir + student_folder
    
    student = Student(student_name, student_folder, student_archive, student_extract)
    return student

def get_already_graded_students():
    global grades_file
    already_graded_students = []
    if os.path.isfile(grades_file):
        fp = open(grades_file, "r")
        already_graded_students = list(map(lambda x: x.split(',')[0], fp.readlines()))
        fp.close()
    return already_graded_students

def generate_students():
    global archive_types
    global grading_dir

    grading_files = os.listdir(grading_dir)
    already_graded_students = get_already_graded_students()
    students = []
    for fi in grading_files:
        fi_parts = os.path.splitext(fi)
        if fi_parts[1] in archive_types:
            student_archive = re.match("\d{3,6}-\d{3,6} - \w+ \w+.*", fi)
            if student_archive:
                student = create_student(fi)
                if student.name not in already_graded_students:
                    students.append(student)
                else:
                    print(bcolors.RED + "skipping %s" % student.name + bcolors.ENDC)
            else:
                print("Found %s that does not match student archive regex" % fi)
        else:
            print("Found %s that is not an archive" % fi)
            os.remove(grading_dir + fi)
    return sorted(students, key=lambda k:k.name)

def create_grading_dir(d2l_archive):
    global grading_dir
    if not os.path.isdir(grading_dir):
        unpack_file(d2l_archive, grading_dir)
    return grading_dir

def get_latest_file(files):
    latest_time = 0
    latest_file = ""
    for f in files:
        modtime = os.path.getmtime(f)
        if modtime > latest_time:
            modtime = latest_time
            latest_file = f
    return latest_file

def prune_grading_dir(grading_dir):
    global archive_types
    all_files = os.listdir(grading_dir)
    file_paths = list(map(lambda x: "grading_dir/" + x, all_files))
    file_dict = {}
    files_to_remove = []
    for archive in file_paths:
        if os.path.splitext(archive)[1] not in archive_types:
            files_to_remove.append(archive)
            continue
        archive_parts = archive.split(' - ')
        folder_name = archive_parts[3].split('.')[0]
        if folder_name not in file_dict:
            file_dict[folder_name] = [archive]
        else:
            file_dict[folder_name].append(archive)
    for k,v in file_dict.items():
        latest_file = get_latest_file(v)
        v.remove(latest_file)
        if len(v) > 0:
            files_to_remove.extend(v)

    for fi in files_to_remove:
        if os.path.isdir(fi):
            shutil.rmtree(fi)
        else:
            os.remove(fi)

def get_python_files(extract_path):
    script_paths = []
    if "__MACOSX" in os.listdir(extract_path):
            shutil.rmtree(extract_path + "/__MACOSX")
    for (dirpath, dirnames, filenames) in os.walk(extract_path):
        for f in filenames:
            if os.path.splitext(f)[1] == ".py":
                script_paths.append(dirpath + "/" + f)
    return sorted(script_paths)

def isint(val):
    try:
        int(val)
        return True
    except:
        return False

def get_selection(python_scripts):
    print("[-] skip")
    for idx, fn in enumerate(python_scripts):
        if "/" in fn:
            parts = fn.split("/")
            fn = parts[-2] + "/" + parts[-1]
        print("[%s] %s" % (idx, fn))
    sel_number = " "
    while not isint(sel_number[0]) and sel_number != "-":
        sel_number =  input(bcolors.GREEN + "Enter a selection\n" + bcolors.ENDC)
    if sel_number == "-":
        selection = "skip"
    else:
        sel_args = sel_number[1:]
        sel_number = int(sel_number[0])
        selection = python_scripts[sel_number]
    return selection,sel_args

def handle_selection(selection, args, student):
    if selection == "skip":
        return 0
    elif selection == "grade":
        grade = str(input(bcolors.RED + "What grade does this peasant deserve?\n" + bcolors.ENDC))
        if add_grade(student, grade) == 0:
            shutil.rmtree(student.extract_path)
            return 0
    else:
        run_file(selection, args)

def replace(file_path, pattern, subst):
    fh, abs_path = tempfile.mkstemp()
    with os.fdopen(fh, 'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    os.remove(file_path)
    shutil.move(abs_path, file_path)

def add_grade(student, grade):
    global grades_file
    write_line = "%s,%s\n" % (student.name, grade)
    yes = ['y', 'Y', 'yes']
    
    try:
        gf = open(grades_file, "r")
    except:
        gf = open(grades_file, "w")
        gf.close()
        gf = open(grades_file, "r")
    curr_content = gf.readlines()
    gf.close()
    found = False
    for line in curr_content:
        if student.name in line:
            ow = input("Found entry: %s, overwrite? (y/n/c)" % line)
            if ow in yes:
                found=True
                replace(grades_file, line, write_line)
                return 0
            elif ow == "c":
                return 1
            else:
                found=True
                return 0
        
    if not found :
        gf = open(grades_file, "a")
        gf.write(write_line)
        gf.close()
        return 0

def run_file(f, fargs):
    fp = open(f, "r")
    lines = fp.readlines()[:10]
    fp.close()
    comment_block=False
    for line in lines:
        triple_quotes = line.strip().startswith("\"\"\"")
        if triple_quotes:
            comment_block = not comment_block
        if comment_block:
            print(line.rstrip())
        if line.strip().startswith("#"):
            print(line.rstrip())

    run_line = "python %s %s" % (f, fargs)
    try:
        p = subprocess.call(run_line, shell=True)
    except KeyboardInterrupt:
        print("CTRL-C caught, script has been killed!")

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def remove_header(lines):
    new_script = []
    comment_block = False
    for idx, line in enumerate(lines):
        is_comment = False
        triple_quotes = line.strip().startswith("\"\"\"")
        if triple_quotes:
            comment_block = not comment_block
        if comment_block or line.strip().startswith("#"):
            is_comment = True
        if not is_comment and idx < 10:
            new_script.append(line)
        elif idx > 10:
            new_script.append(line)
    return new_script

def compare_scripts(script_one, script_two):
    scripts = [script_one, script_two]
    contents = []
    for script in scripts:
        fp = open(script, 'r')
        script_contents = fp.readlines()
        fp.close()
        stripped_contents = remove_header(script_contents)
        contents.append(stripped_contents)
    comp = similar(str(contents[0]), str(contents[1]))
    return comp

def detect_cheaters(python_scripts):
    script_lists = []
    keyword_lists = []
    words = ["file", "file ", "file_"]
    for i in range(1,3):
        keywords = list(map(lambda x: x + str(i), words))
        for j in range(1, 3):
            version = str(j) + "." + str(i)
            version_two = str(j) + "_" + str(i)
            keywords.append(version)
            keywords.append(version_two)
        keyword_lists.append(keywords)
    
    for keyword_list in keyword_lists:
        matching_scripts = []
        for s in python_scripts:
            if any(word in s.lower() for word in keyword_list):
                matching_scripts.append(s)
        script_lists.append(matching_scripts)

    greatest_vals = {}
    for script_list in script_lists:
        for script_one in script_list:
            print(script_one)
            greatest_val = 0
            for script_two in script_list:
                if script_one == script_two:
                    continue
                cheat_val = compare_scripts(script_one, script_two)
                if cheat_val > greatest_val:
                    greatest_val = cheat_val
            greatest_vals[script_one] = greatest_val
            print(greatest_val)
    print(greatest_vals)

def main():
    global grading_dir
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument('-c', '--cheating', required=False, action='store_true')
    args = parser.parse_args()

    create_grading_dir(args.file)
    prune_grading_dir(grading_dir)
    students = generate_students()
    all_scripts = []

    for student in students:
        print(bcolors.GREEN + "\n" + student.name + bcolors.ENDC)
        unpack_file(student.archive_path, student.extract_path)
        python_scripts = get_python_files(student.extract_path)
        if args.cheating:
            all_scripts.extend(python_scripts)
        else:
            python_scripts.insert(0, "grade")
            while(1):
                selection,sel_args = get_selection(python_scripts)
                status = handle_selection(selection, sel_args, student)
                if status == 0:
                    break
                else:
                    continue
    if args.cheating:
        detect_cheaters(all_scripts)

if __name__ == "__main__":
    main()

