# FNP Grading Helper

### Usage

Download files from D2L. They will be in a wonky format: '1232417 - blah blah blah - PM - studentname-HWX.zip'
Convert them to a more suitable format: 'studentname-HWX.zip' with the following command,
```
for i in *.zip; do mv "$i" "$(echo "$i" | sed 's/ //g' | sed 's/.*AM-//;s/.*PM-//'; )"; done
```

From a parent directory run the following command,
```
python grading_helper.py grading_directory/
```

### Requirements
 - python3 

### Features
 - etc, etc, etc

### TODO
 - Document grades in a CSV file.
 - Automatically grade students with improper filenames.
 - Automate D2L grading submission process.
