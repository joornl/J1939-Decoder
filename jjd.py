#!/usr/bin/env python3
import os
import re
import sys
import getopt
import sqlite3

#
# Globals
#
DB_FILE="j1939da-pgn-spn-oct22.db"
VERSION="20240725.00"

#
# Subroutines
#
def usage():
    print("""
Usage (Version: """ + VERSION + """):
  """ + os.path.basename(sys.argv[0]) + """ [-d <sqlite3 DB file>] [-i -|<file>] [-p <pgn>] \
[-s <spn>] [-a <src add>] [CAN message]

Flags:
  -a = Source address (as integer or hexadecimal with leading 0x)
  -d = Location of SQLite3 DB file (default: j1939da-pgn-spn-oct22.db in same 
       directory as this script)
  -i = Input file containing raw CAN messages, or read from 
       STDIN if argument is \"-\"
  -p = PGN number (as integer or hexadecimal with leading 0x)
  -s = SPN number

Sample CAN messages (2 supported formats):
 can0  18FEF121   [8]  C7 FF FF C3 00 FF FF F0
 (1715275504.474510) can0 0CF00203#CC0000FFF00000FF

Example usage:
  """ + os.path.basename(sys.argv[0])\
  + """ \"can0  18FEF121   [8]  C7 FF FF C3 00 FF FF F0\"
  """ + os.path.basename(sys.argv[0])\
  + """ \"(1715275504.474510) can0 0CF00203#CC0000FFF00000FF\"
  """ + os.path.basename(sys.argv[0]) + """ -p 61443 -s 3357
  """ + os.path.basename(sys.argv[0]) + """ -p 61443
  """ + os.path.basename(sys.argv[0]) + """ -p OxF003
  """ + os.path.basename(sys.argv[0]) + """ -i can-msgs.txt
  echo \"(1715275504.474510) can0 0CF00203#CC0000FFF00000FF\" | """\
  + os.path.basename(sys.argv[0]) + """ -i -
  """ + os.path.basename(sys.argv[0]) + """ -a 249
  """ + os.path.basename(sys.argv[0]) + """ -a 0xF9
  """)


def procLine(line, dbcon):
    can_id = None
    can_data = None
    dest_add = None
    dest = None
    prg_nm = sys.argv[0]

    # Sample line:
    #  can0  18FEF121   [8]  C7 FF FF C3 00 FF FF F0
    # or
    #  (1715275504.466376) can0 0C0B2A17#FDFFFFFFFFFFFFEA
    #
    # Guess the format
    regx1 = re.compile("\s*can\d+\s+(\w+)\s+\[\d+\]\s+(.*)")
    regx2 = re.compile("\(\d+\.\d+\) can\d+ (\w+)#(\w+)")
    mobj = re.match(regx1, line)
    if (mobj):
        can_id = mobj.group(1)
        can_data = mobj.group(2)
    else:
        mobj = re.match(regx2, line)
        if (mobj):
            can_id = mobj.group(1)
            can_data = mobj.group(2)
            can_data = " ".join(can_data[i:i+2] for i in range(0, len(can_data), 2))

    if can_id and can_data:
        pass
    else:
        print("ERROR - Unsupported CAN message!")
        return None

    if len(can_id) != 8:
        print("ERROR - Invalid CAN ID [" + line + "]")
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
    data_l = can_data.split()

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

    print("%12s: %s\n" % ("Raw CAN msg", line.strip()))
    print("%12s: %s (%s)" % ("PGN", label, pgn))
    print("%12s: %s" % ("Acronym", acronym))
    cmd = prg_nm + " -p " + str(pgn)
    print("%12s: %s" % ("PGN Details", cmd))
    print("%12s: %s (%d)" % ("Source Add", source, sa))
    if dest_add:
        print("%12s: %s (%d)" % ("Dest Add", dest, dest_add))
    print("\n")

    q = ""\
      + "select "\
        + "spn.label, "\
        + "spn.spn, "\
        + "spn.byte_num, "\
        + "spn.bit_len, "\
        + "spn.bit_start, "\
        + "spn.scale_factor, "\
        + "spn.offset, "\
        + "spn.unit "\
      + "FROM "\
        + "pgn pgn, "\
        + "spn spn "\
      + "WHERE "\
        + "pgn.pgn = ? "\
        + "and pgn.pgn_id = spn.pgn_id"

    dbcur.execute(q, (pgn,))
    for i in dbcur:

        if not i[2]:
            # Skip if SPN is NULL
            print("%12s: %s" % ("SPN", "NULL"))
            continue

        # Skip if byte number is greater than length of CAN
        # message data
        if i[2] > len(data_l):
            # Skip
            continue

        bnum = i[2] - 1
        if data_l[bnum] == "FF":
            continue

        blen = i[3]
        bstart = i[4] - 1
        
        print("%12s: %s (%s)" % ("SPN", i[0], i[1]))
        if blen <= 8:
            # Convert byte in CAN data message to decimal and then to binary
            val = int(data_l[bnum], 16)
            bval = format(val, '#010b')

            # Strip the leading "0b"
            bval = bval[2:]
            bval = bval[bstart:(bstart + blen)]
            val = int(bval, 2)
            val = val * i[5]
            val = val + i[6]
            unit = i[7]
            print("%12s: %sb (%s, %d)" % ("Binary Val", bval, hex(int(bval, 2)), int(bval, 2)))
            if len(unit) == 0:
                print("%12s: %0.2f" % ("Value", val))
            else:
                print("%12s: %0.2f (%s)" % ("Value", val, unit))
        else:
            # Check and see if bit length is > 8 and a multiple of 8. If so, proceed.
            mod_val = blen % 8
            div_val = int(blen / 8)
            val_l = []
            if mod_val == 0 and div_val > 1 and div_val <= 4:
                for bpos in range(0, div_val):
                    val_l.append(data_l[bnum + bpos])

                val_l.reverse()
                hexv = "".join(val_l)
                val = int(hexv, 16)
                val = val * i[5]
                val = val + i[6]
                unit = i[7]
                print("%12s: 0x%s (%d)" % ("Hex Val", hexv, int(hexv, 16)))
                if len(unit) == 0:
                    print("%12s: %0.2f" % ("Value", val))
                else:
                    print("%12s: %0.2f (%s)" % ("Value", val, unit))

        cmd = prg_nm + " -p " + str(pgn) + " -s " + str(i[1])
        print("%12s: %s" % ("Details", cmd))
        print("\n")

    dbcur.close()

    return None



def dispSPNInfo(dbcon, pgn_num, spn_num):
    q = ""\
      + "SELECT "\
        + "spn, "\
        + "label, "\
        + "sp_start_bit, "\
        + "byte_num, "\
        + "bit_len, "\
        + "bit_start, "\
        + "scale_factor, "\
        + "offset, "\
        + "description "\
      + "FROM "\
        + "spn "\
      + "WHERE pgn_id = (SELECT pgn_id FROM pgn WHERE pgn = ?) AND spn = ?"

    dbcur = dbcon.cursor()
    dbcur.execute(q, (pgn_num, spn_num))
    for i in dbcur:
        print("%14s: %s (%s)" % ("SPN", i[1], i[0]))
        print("%14s: %s" % ("SP Start Bit", i[2]))
        print("%14s: %s" % ("Byte Num", i[3]))
        print("%14s: %s" % ("Bit Len", i[4]))
        print("%14s: %s" % ("Bit Start", i[5]))
        print("%14s: %s" % ("Scale Factor", i[6]))
        print("%14s: %s\n" % ("Offset", i[7]))
        print("%s:" % ("Description",))
        print("%s" % (i[8].strip('"')))

    # Close DB cursor
    dbcur.close()

    return None


def dispSAInfo(src_add):
    q = ""\
      + "SELECT "\
        + "sa, "\
        + "label "\
      + "FROM "\
        + "sa "\
      + "WHERE sa = ?"

    dbcur = dbcon.cursor()

    # Check if source address is supplied with leading hexadecimal designator
    if src_add.startswith("0x"):
        src_add = int(src_add, 16)

    dbcur.execute(q, (src_add, ))
    for i in dbcur:
        print("%14s: %s" % ("Source Add", i[0]))
        print("%14s: %s" % ("Name", i[1]))

    # Close DB cursor
    dbcur.close()

    return None


def dispPGNInfo(dbcon, pgn):
    prg_nm = sys.argv[0]

    q = ""\
      + "SELECT "\
        + "pgn, "\
        + "acronym, "\
        + "label, "\
        + "description "\
      + "FROM "\
        + "pgn "\
      + "WHERE pgn = ?"

    dbcur = dbcon.cursor()

    # Check if PGN is supplied as a hexadecimal value
    if pgn.startswith("0x"):
        pgn = int(pgn, 16)

    dbcur.execute(q, (pgn, ))
    for i in dbcur:
        print("%14s: %s" % ("PGN", i[0]))
        print("%14s: %s" % ("Acronym", i[1]))
        print("%14s: %s" % ("Label", i[2]))
        print("")
        print("%s" % ("Description:",))
        print("%s" % (i[3],))

    # Get associated SPNs
    q = ""\
      + "SELECT "\
        + "spn, "\
        + "label "\
      + "FROM "\
        + "spn "\
      + "WHERE pgn_id = (SELECT pgn_id FROM pgn WHERE pgn = ?)"

    print("\n\nAssociated SPNs:")
    dbcur = dbcon.cursor()
    dbcur.execute(q, (pgn, ))
    for n,i in enumerate(dbcur, 1):
        print("(%d)" % (n,))
        print("%12s: %s" % ("SPN", i[0]))
        print("%12s: %s" % ("Label", i[1]))
        cmd = prg_nm + " -p " + str(pgn) + " -s " + str(i[0])
        print("%12s: %s" % ("Details", cmd))
        print("\n")

    # Close DB cursor
    dbcur.close()

    return None



#
# Main
#
infile  = None
dbfile  = None
ifo     = None
pgn_num = None
spn_num = None
src_add = None

if len(sys.argv) == 1:
    usage()
    sys.exit(0)

try:
    (opts, args) = getopt.getopt(sys.argv[1:], "a:i:d:p:s:")
except getopt.GetoptError as e:
    print("ERROR - getopt() [" + str(e) + "]")
    usage()
    sys.exit(1)

for (k,v) in opts:
    if k == "-a":
        src_add = v
    elif k == "-i":
        if v == "-":
            ifo = sys.stdin
        else:
            ifo = open(v)
    elif k == "-d":
        dbfile = v
    elif k == "-p":
        pgn_num = v
    elif k == "-s":
        spn_num = v

if not dbfile:
    dbfile = DB_FILE
    if not os.path.exists(dbfile):
        print("ERROR - " + dbfile + ": Not found!")
        sys.exit(1)

# Open DB file
try:
    dbcon = sqlite3.connect(dbfile)

    #dbcur = dbcon.cursor()

    # If "-p" and "-s" flags used, query and return SPN info
    if pgn_num and spn_num:
        dispSPNInfo(dbcon, pgn_num, spn_num)
        sys.exit(0)

    # If "-p" is the only flag used, query and return PGN info and all the  
    # SPNs (and associated info) covered by that PGN
    if pgn_num:
        dispPGNInfo(dbcon, pgn_num)
        sys.exit(0)

    if src_add:
        dispSAInfo(src_add)
        sys.exit(0)

    if ifo:
        for n,line in enumerate(ifo, 1):
            line = line.rstrip()
            print("\n\n===Begin CAN message #" + str(n) + "===\n")
            procLine(line, dbcon)
            print("===End CAN message #" + str(n) + "===\n\n")
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
