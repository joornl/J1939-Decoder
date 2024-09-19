#!/usr/bin/env python3
import sys
import re
import os
import getopt
import sqlite3

#
# Definitions
#
NUM_FLDS = 46
#x REQD_FLD_IDX_L = [4, 5, 6, 7, 20, 21, 22, 23, 24, 29, 34, 35]
PGN_FLD_MAP = {
  "pgn": 4,
  "label": 5,
  "acronym": 6,
  "description": 7}
SPN_FLD_MAP = {
  "transmission_rate": 15,
  "sp_start_bit": 20,
  "spn": 21,
  "label": 22,
  "description": 23,
  "bit_len": 24,
  "unit": 29,
  "scale_factor": 34,
  "offset": 35}


#
# Subroutines
#
def usage():
    print("""
Usage: 
  """ + os.path.basename(sys.argv[0]) + """ [-h] <tab-separated file>

  Flags:
    -h    display header

Example:
  """ + os.path.basename(sys.argv[0]) + """ -h j1939da-pgn-spn-oct22.tsv
  """ + os.path.basename(sys.argv[0]) + """ j1939da-pgn-spn-oct22.tsv
""")


def getHeader(tsv_file, regx):
    hline = ""
    with open(tsv_file) as fo:
        for line in fo:
            if line.startswith('Revised\tPG Revised\tSP Revised'):
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

    # First check and see if pgn is already in pgn table
    q = "SELECT count(*) FROM pgn where pgn = ?"
    res = cur.execute(q, (flds_l[PGN_FLD_MAP["pgn"]],))
    for row in res:
        if row[0] == 0:
            pgn_insert = True

    if pgn_insert:
        # Check if pgn is a number
        try:
            pgn = int(flds_l[PGN_FLD_MAP["pgn"]])
        except ValueError as e:
            err = "PGN is not INTEGER!"
            rv = 0
            return (rv, err)

        q = ""\
          + "INSERT INTO pgn "\
          + "("\
            + "pgn, "\
            + "label, "\
            + "acronym, "\
            + "description"\
          + ") "\
          + "VALUES "\
            + "(?, ?, ?, ?)"

        try:
            cur.execute(q, (flds_l[PGN_FLD_MAP["pgn"]], 
                            flds_l[PGN_FLD_MAP["label"]], 
                            flds_l[PGN_FLD_MAP["acronym"]], 
                            flds_l[PGN_FLD_MAP["description"]]))
            dbcon.commit()
        except Error as e:
            err = str(e)
            rv = 1 

    # Extract/calculate the following values:
    #  - values for byte_num and bit_start from sp_start_bit
    #  - value for bit_len
    #  - value for bit_start
    byte_num = None
    bit_len = None
    bit_start = None

    ssb = flds_l[SPN_FLD_MAP["sp_start_bit"]]
    if "." in ssb:
        # Value would be somthing like "2.1", "4.3", etc.
        ssb_flds_l = ssb.split(".") 
        byte_num = int(ssb_flds_l[0])
        bit_start = int(ssb_flds_l[1])

    # The value of bit length is a string that looks like:
    #  - 11 bits
    #  - 1 byte
    #  - 3 bytes
    bl = flds_l[SPN_FLD_MAP["bit_len"]]
    mobj = re.match("(\d+) (bytes|bits|byte)", bl)
    if mobj:
        if mobj.group(2) == "bits":
            bit_len = int(mobj.group(1))
        elif mobj.group(2) == "byte" or mobj.group(2) == "bytes":
            bit_len = int(mobj.group(1)) * 8
        else:
            rv = 1
            err = "Bits, Bytes or Byte not found in SP Length [" + bl \
                + "] [PGN=" + flds_l[PGN_FLD_MAP["pgn"]] + "; "\
                + "SPN=" + flds_l[SPN_FLD_MAP["spn"]] + "]"
            return (rv, err)
#j    else:
#j        rv = 1
#j        err = "Unexpected SP Length value [" + bl + "] [PGN = "\
#j            + flds_l[PGN_FLD_MAP["pgn"]] + "; "\
#j            + "SPN=" + flds_l[SPN_FLD_MAP["spn"]] + "]"
#j        return (rv, err)
        

    # Insert into spn table
    q = ""\
      + "INSERT INTO spn "\
      + "("\
        + "spn, "\
        + "pgn_id, "\
        + "label, "\
        + "sp_start_bit, "\
        + "byte_num, "\
        + "bit_start, "\
        + "bit_len, "\
        + "unit, "\
        + "scale_factor, "\
        + "offset, "\
        + "transmission_rate, "\
        + "description"\
      + ") "\
      + "VALUES "\
        + "(?, (SELECT pgn_id FROM pgn WHERE pgn = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

    try:
        cur.execute(q, (flds_l[SPN_FLD_MAP["spn"]], 
                        flds_l[PGN_FLD_MAP["pgn"]], 
                        flds_l[SPN_FLD_MAP["label"]], 
                        flds_l[SPN_FLD_MAP["sp_start_bit"]], 
                        byte_num,
                        bit_start,
                        bit_len,
                        flds_l[SPN_FLD_MAP["unit"]], 
                        flds_l[SPN_FLD_MAP["scale_factor"]], 
                        flds_l[SPN_FLD_MAP["offset"]], 
                        flds_l[SPN_FLD_MAP["transmission_rate"]], 
                        flds_l[SPN_FLD_MAP["description"]]))
        dbcon.commit()
    except sqlite3.DatabaseError as e:
        err = flds_l[PGN_FLD_MAP["pgn"]] + ":" + flds_l[SPN_FLD_MAP["spn"]] + "  " + str(e)
        rv = 1 

    return (rv, err)


def createTables(dbcon):
    q = ""\
      + "CREATE TABLE pgn ("\
        + "pgn_id INTEGER PRIMARY KEY, "\
        + "pgn INTEGER, "\
        + "label TEXT, "\
        + "acronym TEXT, "\
        + "description TEXT"\
      + ")"

    cur = dbcon.cursor()
    cur.execute(q)
    dbcon.commit()

    q = ""\
      + "CREATE TABLE spn ("\
        + "spn_id INTEGER PRIMARY KEY, "\
        + "spn INTEGER, "\
        + "pgn_id INTEGER REFERENCES pgn(pgn_id) ON DELETE CASCADE "\
          + "ON UPDATE CASCADE, "\
        + "sp_start_bit TEXT, "\
        + "byte_num INTEGER, "\
        + "bit_len INTEGER, "\
        + "bit_start INTEGER, "\
        + "unit TEXT, "\
        + "scale_factor FLOAT, "\
        + "offset FLOAT, "\
        + "label TEXT, "\
        + "transmission_rate TEXT, "\
        + "description TEXT"\
      + ")"

    cur.execute(q)
    dbcon.commit()


    q = ""\
      + "create unique index spn_spn_pgnid on spn(spn, pgn_id)"
    cur.execute(q)
    dbcon.commit()

    return True


#
# Main
#

show_flds = False

try:
    (opts, args) = getopt.getopt(sys.argv[1:], "h")
except getopt.GetoptError as e:
    print("ERROR - getopt() [" + str(e) + "]")
    usage()
    sys.exit(1)

for (k,v) in opts:
    if k == "-h":
        show_flds = True


if len(args) != 1:
    usage()
    sys.exit(1)


tsvfile = args[0]

regx1 = re.compile("^\t\t\t\t[0-9]+")
regx2 = re.compile("^\(R\)\t[\t(R)]|^\t\(R\)[\t\(R\)]")
regx3 = re.compile("^\t\t\t\tN/A")
header_d = getHeader(tsvfile, regx1)

if show_flds:
    print(header_d)
    sys.exit(0)


dbfile = os.path.basename(tsvfile.replace(".tsv", ".db"))

# Ensure that db file does not already exist
if os.path.exists(dbfile):
    msg = "ERROR - " + dbfile + ": already exists! Please move/remove it."
    print(msg)
    sys.exit(1)

try:
    dbcon = sqlite3.connect(dbfile)
    createTables(dbcon)

    prev_line = ""
    with open(tsvfile) as fo:
        for n,line in enumerate(fo, 1):
            mobj1 = regx1.match(line)
            mobj2 = regx2.match(line)
            if mobj1 or mobj2:
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
                    mobj3 = regx3.match(line)
                    if mobj3:
                        # Line starts with: \t\t\t\tN/A...
                        # Not applicable lines..
                        break
    
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
