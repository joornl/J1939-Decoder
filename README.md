# J1939-Decoder

The J1939 Decoder package is a set of scripts that will allow one to decode 
J1939 messages. Simply running the script "jjd.py" without any arguments will 
display the syntax and usage examples.


## DEPENDENCIES
    In order to use these scripts one has to purchase/acquire the 
    "J1939 Digital Annex" spreadsheet files from SAE (Society of Automotive 
    Engineers). The .xlsx file used for the development of these scripts is: 
    J1939DA Oct22.xlsx


## USAGE INSTRUCTIONS
### Step 1:
    The "J1939 Digital Annex" spreadsheet used ("J1939DA Oct22.xlsx") had 17 
    sheets. Of them, the following sheets were exported as tab separated values
    (Note: tab separated values, not comma separated values) using LibreOffice 
    Calc:
        (1) SPs & PGs
        (2) Global Source Addresses (B2)
        (3) IG1 Source Addresses (B3)

    The export to tab separated values resulted in the following files:
      (1) j1939da-pgn-spn-oct22.tsv (file size: 16838169 bytes)
      (2) j1939da-source-global-sa-oct22.tsv (file size: 16861 bytes)
      (3) j1939da-source-add-hwy-oct22.tsv (file size: 7805 bytes)

## Step 2:

    The next step is to build the SQLite3 database. Use the following commands 
    as a guide. First, create the database with the SPs & PGs sheet like so:
      $ ./j1939-pgn-spn-ingest.py j1939da-pgn-spn-oct22.tsv

    Add information from the global source addresses sheet to the created 
    database like so:
      $ ./j1939-source-add-ingest.py -d j1939da-pgn-spn-oct22.db j1939da-source-global-sa-oct22.tsv

    Next, add the source addresses for highway equipment like so:
      $ ./j1939-source-add-ingest.py -d j1939da-pgn-spn-oct22.db j1939da-source-add-hwy-oct22.tsv

## Step 3: (Optional)
    In the jjd.py script, right at the top, in a section labeled "Globals", the
    location of the SQLite3 database is specified. Adjust that, if required, so 
    that jjd.py may be invoked without having to supply the "-d" flag.

## Step 4:
jjd.py is ready for use now. Simply running like so:
      `$ ./jjd.py`
will display syntax and examples of usage.


---

# CAN ID Decoder
Give a CAN ID, like 0C0A002A, the `jcd.py` script will decode that ID into comma-separated values, one line for each SPN, like so:

	CAN ID,PGN,Acronym,Dest Add,Source Add,SPN
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Cruise Control Disable Command (5603)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Cruise Control Resume Command (5604)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Cruise Control Pause Command (5605)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Cruise Control Set Command (9843)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Idle Speed Request (8438)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Idle Control Enable State (8439)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Idle Control Request Activation (8440)
	0C0A002A,Cruise Control / Vehicle Speed 2 (2560),CCVS2,GLOBAL (255),Headway Controller (42),Remote Vehicle Speed Limit Request (9569)

## DEPENDENCIES
`jcd.py` also depends on the "J1939 Digital Annex" spreadsheet files from SAE (Society of Automotive Engineers).
