#!/usr/bin/env python3
import os
import sys
import getopt
import sqlite3

#
# Globals
#
DB_FILE="j1939da-pgn-spn-oct22.db"
VERSION="20241204.00"

#
# Subroutines
#
def usage():
    print("""
Usage (Version: """ + VERSION + """):
  """ + os.path.basename(sys.argv[0]) + """ [-d <sqlite3 DB file>] [-i -|<file>] [CAN ID]

Flags:
  -d = Location of SQLite3 DB file (default: j1939da-pgn-spn-oct22.db in same 
       directory as this script)
  -i = Input file containing CAN IDs, or read from STDIN if argument is \"-\"

Example usage:
  """ + os.path.basename(sys.argv[0])\
  + """ 18FEF121
  """ + os.path.basename(sys.argv[0]) + """ -i can-ids.txt
  echo 0CF00203 | """ + os.path.basename(sys.argv[0]) + """ -i -

Description:
  Given a CAN ID, this script will display the PGN, PGN acronym, destination 
  address, source address and all related SPNs as comma-separated values.

  """)


def procLine(can_id, dbcon):
    prg_nm = sys.argv[0]
    dest_add = None

    if len(can_id) != 8:
        ## Check if can_id is 7 characters long. If CAN ID starts with 0, candump 
        ## seems to drop the 0. Let's add it in that case.
        if len(can_id) == 7:
            can_id = "0" + can_id
        else:
            print("ERROR - Invalid CAN ID [" + can_id + "]")
            return False

    pri_r_dp = can_id[0:2]
    ival = int(pri_r_dp, 16)
    if (ival & 3) != 0:
        msg = "ERROR - Bits 25 and 24 (little-endian) of 29-bit CAN frame "\
            + "not '00' is currently unsupported!"
        print(msg)
        return False

    # Check and see if PDU1 or PDU2 format
    pgn_b1 = can_id[2:4]
    ival = int(pgn_b1, 16)
    if ival < 240:
        pgn = pgn_b1 + "00"
        dest_add = can_id[4:6]
    else:
        pgn = can_id[2:6]

    sa = can_id[6:8]

    # Convert pgn and sa from hex to decimal
    pgn = int(pgn, 16)
    sa = int(sa, 16)

    if dest_add:
        dest_add = int(dest_add, 16)

    q = ""\
      + "SELECT "\
        + "label, "\
        + "acronym, "\
        + "(SELECT label FROM sa WHERE sa = ?), "\
        + "(SELECT label FROM sa WHERE sa = ?) "\
      + "FROM "\
        + "pgn "\
      + "WHERE "\
        + "pgn = ?"

    source = ""

    # Get a DB cursor
    dbcur = dbcon.cursor()

    if dbcur.execute(q, (sa, dest_add, pgn)):
        row = dbcur.fetchone()
        if row:
            label = row[0]
            acronym = row[1]
            source = row[2]
            if row[3]:
                dest = row[3]
        else:
            print("ERROR - PGN=" + str(pgn) + " and/or SA=" + str(sa) + " not in DB!")
            dbcur.close()
            return None

    q = ""\
      + "select "\
        + "spn.label, "\
        + "spn.spn "\
      + "FROM "\
        + "pgn pgn, "\
        + "spn spn "\
      + "WHERE "\
        + "pgn.pgn = ? "\
        + "and pgn.pgn_id = spn.pgn_id"

    dbcur.execute(q, (pgn,))
    for n,i in enumerate(dbcur):
        if n == 0:
    	    # Print header
    	    print("CAN ID,PGN,Acronym,Dest Add,Source Add,SPN")

        print("%s," % can_id.strip(), end="")
        print("%s (%s)," % (label, pgn), end="")
        print("%s," % acronym, end="")
        if dest_add:
            print("%s (%d)," % (dest, dest_add), end="")
        else:
            print("GLOBAL (255),", end="")
        print("%s (%d)," % (source, sa), end="")
        print("%s (%s)" % (i[0], i[1]))

    dbcur.close()

    return None


#
# Main
#
infile  = None
dbfile  = None
ifo     = None

if len(sys.argv) == 1:
    usage()
    sys.exit(0)

try:
    (opts, args) = getopt.getopt(sys.argv[1:], "i:d:")
except getopt.GetoptError as e:
    print("ERROR - getopt() [" + str(e) + "]")
    usage()
    sys.exit(1)

for (k,v) in opts:
    if k == "-i":
        if v == "-":
            ifo = sys.stdin
        else:
            ifo = open(v)
    elif k == "-d":
        dbfile = v

if not dbfile:
    dbfile = DB_FILE
    if not os.path.exists(dbfile):
        print("ERROR - " + dbfile + ": Not found!")
        sys.exit(1)

# Open DB file
try:
    dbcon = sqlite3.connect(dbfile)

    if ifo:
        for n,line in enumerate(ifo, 1):
            line = line.rstrip()
            procLine(line, dbcon)
            print("\n")
    else:
        procLine(args[0], dbcon)

except sqlite3.DatabaseError as e:
    print("ERROR - DB Exception [" + str(e) + "]")
finally:
    # Close db connection
    dbcon.close()
    rc = 0

if ifo:
    ifo.close()

# Exit gracefully
sys.exit(rc)
