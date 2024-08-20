#!/bin/bash

if [ $# -ne 2 ]; then
        echo "Usage: $0 <input_directory> <output_directory>"
        exit 1
fi
input_directory=$1
output_directory=$2

 

#Check if directories exist.
if [ ! -d $1 ]; then
        echo "Input directory was not found."
        exit 2
fi
if [ ! -d $2 ]; then
        echo "Output directory was not found."
        read -p "Would you like to create this directory? [Y/n]" response
        case $response in [yY]|'')
                echo "Creating directory $2 in working directory" && pwd
                mkdir $2
        esac
        case $response in [nN]|'')
                echo "No directory will be created. Aborting..."
                exit 0
        esac
fi
echo "\n"

 

#If the directories exist, continue with the script
for file in "$input_directory"/*; do
        if [ -f "$file" ]; then
                echo "Processing file: $file"
                filename="processed_"$(basename "$file")
                python3 jjd.py -i $file > "$output_directory/$filename"
                echo "Sent processed file to $output_directory"
                echo "\n"
        fi
done
