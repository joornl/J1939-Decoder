#!/usr/bin/env python3
import sys
import re
import os
import getopt
import sqlite3

#
# Definitions
#
NUM_FLDS = 5
REQD_FLD_IDX_L = [1, 2]
SA_FLD_MAP = {
  "sa": 1,
  "label": 2}

#
# Subroutines
#
def usage():
    print("""
Usage: 
  """ + os.path.basename(sys.argv[0]) + """ [-h] -d <DB file> <tab-separated file>

  Flags:
    -h    display header
    -d    argument following flag specifies existing DB file

Example:
  """ + os.path.basename(sys.argv[0]) + """ -h j1939da-source-add-oct22.tsv
  """ + os.path.basename(sys.argv[0]) + """ -d j1939da-pgn-spn-oct22.db j1939da-source-add-oct22.tsv
  """ + os.path.basename(sys.argv[0]) + """ -d j1939da-pgn-spn-oct22.db j1939da-source-add-hwy-oct22.tsv """)


def getHeader(tsv_file, regx):
    hline = ""
    with open(tsv_file) as fo:
        for line in fo:
            if line.startswith('Revised\tFunction ID\tFunction Description'):
                hline = line.rstrip()
            elif regx.match(line):
                break
            elif hline != "":
                hline += line.rstrip()
            else:
                # Probably a line before header. Let's just skip it.
                continue

    hflds_l = hline.split('\t')

    ret_d = {}
    for n,fld in enumerate(hflds_l):
        ret_d[n] = fld

    return ret_d



def transTabsToSpaces(iline):
    in_dq = False
    oline = ""

    for c in iline:
        if c == '"':
            # Toggle if already inside double quote
            if in_dq:
                in_dq = False
            else:
                in_dq = True
    
        if c == '\t' and in_dq:
            c = ' '
    
        oline += c
    
    return oline


def procLine(line, dbcon):
    rv = 0
    err = ""
    pgn_insert = False

    flds_l = line.split('\t')
#x    print("num_flds:", len(flds_l))

    if len(flds_l) > NUM_FLDS:
        # There are tab characters in between double quotes. Let's convert
        # them to spaces
        line = transTabsToSpaces(line)
        flds_l = line.split('\t')
        
        if len(flds_l) != NUM_FLDS:
            err = "Number of fields != " + str(NUM_FLDS)\
                + "! [" + str(len(flds_l)) + "]"
            rv = 1
            return (rv, err)

    # Create a cursor
    cur = dbcon.cursor()

    # Insert into spn table
    q = ""\
      + "INSERT INTO sa "\
      + "("\
        + "sa, "\
        + "label"\
      + ") "\
      + "VALUES "\
        + "(?, ?)"

    try:
        cur.execute(q, (flds_l[SA_FLD_MAP["sa"]], 
                        flds_l[SA_FLD_MAP["label"]]))
        dbcon.commit()
    except sqlite3.DatabaseError as e:
        err = str(e)
        rv = 1 

    return (rv, err)


def createTable(dbcon):
    q = ""\
      + "CREATE TABLE IF NOT EXISTS sa ("\
        + "sa_id INTEGER PRIMARY KEY, "\
        + "sa INTEGER, "\
        + "label TEXT"\
      + ")"

    cur = dbcon.cursor()
    cur.execute(q)
    dbcon.commit()

    return True


#
# Main
#

show_flds = False
db_file = None

try:
    (opts, args) = getopt.getopt(sys.argv[1:], "hd:")
except getopt.GetoptError as e:
    print("ERROR - getopt() [" + str(e) + "]")
    usage()
    sys.exit(1)

for (k,v) in opts:
    if k == "-h":
        show_flds = True
    elif k == "-d":
        db_file = v


if len(args) != 1:
    usage()
    sys.exit(1)


tsvfile = args[0]

regx1 = re.compile("^\t[0-9]+\t")
header_d = getHeader(tsvfile, regx1)

if show_flds:
    print(header_d)
    sys.exit(0)


# Ensure that db file does not already exist
if not os.path.exists(db_file):
    msg = "ERROR - " + db_file + ": Not found!"
    print(msg)
    sys.exit(1)

try:
    dbcon = sqlite3.connect(db_file)
    createTable(dbcon)

    prev_line = ""
    with open(tsvfile) as fo:
        for n,line in enumerate(fo, 1):
            mobj = regx1.match(line)
            if mobj:
                # Start of "next" line. Write previous line to file
                if prev_line != "":
                    (rv, err) = procLine(prev_line, dbcon)
                    if rv != 0:
                        print("ERROR - " + err + " [Line #: " + str(n) + "]")
    
                prev_line = line
            else:
                if prev_line == "":
                    # Possibly header lines
                    pass
                else:
                    prev_line += line
    
        # Process the last line
        if prev_line != "":
            (rv, err) = procLine(prev_line, dbcon)
            if rv != 0:
                print("ERROR - " + err + " [Last valid line]")

except sqlite3.DatabaseError as e:
    print("ERROR - DB Exception [" + str(e) + "]")
    rc = 1
finally:
    # Close db connection
    dbcon.close()
    rc = 0

# Greaceful exit
sys.exit(rc)
