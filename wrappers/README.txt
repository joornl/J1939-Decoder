===============================================
Bulk-decoder usage: sh bulk-decoder.sh <input_directory> <output_directory>

bulk-decoder.sh takes two inputs: an input directory and an output directory. It will run the jjd.py script 
on all files in the input directory, so make sure that the bulk-decoder is run from a directory where jjd.py can be found.

    input_directory: Filepath of where all unprocessed files that you want to be processed are stored. If the input
    directory is not found, the bulk-decoder will fail. 

    output_directory: Filepath of where all the processed files will be stored. If the output directory
    is not found, the bulk-decoder will give you the option to create said directory. 
        Note: be careful when specifying the output directory. The code can and will overwrite
        contents of a specified directory IF the script-outputed files have the same name as the files in the directory
        (This should not happen under most circumstances)


Example usage:
sh wrappers/bulk-decoder.sh data_types/raw_j1939_cancaptures data_types/processed_j1939_cancaptures
    Will send all processed files from data_types/raw_j1939_cancaptures 
    to the directory data_types/processed_j1939_cancaptures
===============================================