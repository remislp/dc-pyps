"""This module contains functions for choosing and reading a kinetic
mechanism from a mec file generated by DCPROGS.
"""

from Tkinter import*
import tkFileDialog
from array import array
import numpy as np

import mechanism as mec

def choose_mecfile():
    """
    Choose mec file to read.

    Returns
    -------
    mecfile : filename
    version : int
        Version of mec file.
    meclist : list
        Each element is another list containing:
        jstart : int
            Start byte for mechanism in mefile.
        mecnum : int
            Mechanism sequence number in mecfile.
        mectitle : string
        ratetitle : string
    max_mecnum : int
        Number of different mechanisms in mec file.
    """

    root = Tk()
    mecfile = tkFileDialog.askopenfilename(
        initialdir='/home/remis/pDC/data',
        filetypes=[("DC mec", "*.mec"),("DC mec", "*.MEC"),
            ("all files", "*")])
    root.destroy()

    return mecfile

def get_mec_list(mecfile):
    """
    Read list of mechanisms saved in mec file.

    Parameters
    ----------
    mecfile : filename

    Returns
    -------
    version : int
        Version of mec file.
    meclist : list
        Each element is another list containing:
        jstart : int
            Start byte for mechanism in mefile.
        mecnum : int
            Mechanism sequence number in mecfile.
        mectitle : string
        ratetitle : string
    max_mecnum : int
        Number of different mechanisms in mec file.
    """

    f = open(mecfile, 'rb')
    ints = array('i')

    # Read version of mec file. Latest version is 102.
    ints.fromfile(f,1)
    version = ints.pop()

    # Read number of rate sets (records) stored in the file
    ints.fromfile(f,1)
    nrecs = ints.pop()

    # Read byte value for next record
    ints.fromfile(f,1)
    nextrec = ints.pop()

    # Read byte value where last record starts
    ints.fromfile(f,1)
    ireclast = ints.pop()

    # Read start byte value for storage of the ith record
    jstart = np.zeros(nrecs, 'int32')    # jstart()- start byte # for storage of the ith record (2000 bytes)
    for i in range(nrecs):
        ints.fromfile(f, 1)
        jstart[i] = ints.pop()

    meclist = []
    max_mecnum = 0
    for i in range(nrecs):
        f.seek(jstart[i] - 1 + 4)
        ints.fromfile(f,1)
        mecnum = ints.pop()
        if mecnum > max_mecnum:
            max_mecnum = mecnum
        mectitle = f.read(74)
        ints.fromfile(f,5)
        ratetitle = f.read(74)
        
        set = []
        set.append(jstart[i])
        set.append(mecnum)
        set.append(mectitle)
        set.append(ratetitle)
        meclist.append(set)

    f.close()
    return version, meclist, max_mecnum

def choose_mec_from_list(meclist, max_mecnum):
    """
    Choose mechanism from a list of mechanisms in file.

    Parameters
    ----------
    meclist : list
        Each element is another list containing:
        jstart : int
            Start byte for mechanism in mefile.
        mecnum : int
            Mechanism sequence number in mecfile.
        mectitle : string
        ratetitle : string
    max_mecnum : int
        Number of different mechanisms in mec file.

    Returns
    -------
    mecnum : int
        Sequence number of a mechanism to read.
    ratenum : int
        Sequence number of rate set to read.
    """

    # List all mechs and choose one.
    print ' Model #              title'
    ndisp = 0
    for i in range(1, (max_mecnum + 1)):
            present = False
            id = 0
            for j in range(len(meclist)):
                if i == meclist[j][1]:
                    present = True
                    id = j
            if present:
                print i, meclist[id][2]
                ndisp += 1
                if ndisp % 20 == 0:
                    raw_input('\n   Hit ENTER for more... \n')
    try:
        mecnum = int(raw_input(
            "\nWhich mechanism would you like to read (1 to %d)? ... "
            %max_mecnum))
    except:
        print "\nError: model number not entered!"
        mecnum = max_mecnum

    # List and choose rate constants.
    print (
        "\nFor model %d the following rate constants have been stored:"
        %mecnum)

    ndisp = 0
    for i in range(len(meclist)):
       if meclist[i][1] == mecnum:
           print (i+1), meclist[i][3]
           ndisp += 1
           if ndisp % 20 == 0:
               raw_input("\n   Hit ENTER for more... \n")
    try:
        ratenum = (int(raw_input(
            "\nWhich rate set would you like to read?... ")) - 1)
    except:
        print "Error: rate set number not entered!"

    if (ratenum < 0) or (ratenum > len(meclist)):
        print "Error: not valid rate set number!"

    return mecnum, ratenum

def load_mec(mecfile, start):
    """
    Load chosen mec.

    Parameters
    ----------
    mecfile : filename
    start : int
        Start byte in mecfile for mechanism to read.

    Returns
    -------
    mec.Mechanism(RateList, StateList, ncyc) : instance of Mechanism class.
    """

    # Make dummy arrays to read floats, integers and short integers.
    doubles = array('d')
    floats = array ('f')
    ints = array('i')

    f=open(mecfile, 'rb')	# open the .mec file as read only
    f.seek(start - 1);
    ints.fromfile(f, 1)
    version1 = ints.pop()
    ints.fromfile(f, 1)
    mecnum = ints.pop()
    mectitle = f.read(74);

    # Read number of states.
    ints.fromfile(f,1)
    k = ints.pop()
    ints.fromfile(f,1)
    kA = ints.pop()
    ints.fromfile(f,1)
    kB = ints.pop()
    ints.fromfile(f,1)
    kC = ints.pop()
    ints.fromfile(f,1)
    kD = ints.pop()

    # In mec files version=103 all shut states are of type 'C'.
    # Check and leave just one in state 'C', others go as 'B'.
    if kB == 0:
        kB = kC - 1
        kC = 1

    ratetitle = f.read(74)

    # Read size of chess board to draw mechanism.
    ints.fromfile(f,1)
    ilast = ints.pop()
    ints.fromfile(f,1)
    jlast= ints.pop()

    # nrateq- number of non-zero rates in Q; = 2*ncon (always)
    ints.fromfile(f,1)
    nrateq = ints.pop()

    # Number of connections.
    ints.fromfile(f,1)
    ncon = ints.pop()

    # Number of concentration dependent rates
    ints.fromfile(f,1)
    ncdep = ints.pop()

    # Number of ligands
    ints.fromfile(f,1)
    nlig = ints.pop()

    # ? if char mechanism is presnt
    ints.fromfile(f,1)
    chardef = ints.pop()

    # ???
    ints.fromfile(f,1)
    boundef = ints.pop()

    # Number of cycles.
    ints.fromfile(f,1)
    ncyc = ints.pop()

    # Voltage.
    floats.fromfile(f,1)
    vref = floats.pop()

    # Number of voltage dependent rates.
    ints.fromfile(f,1)
    nvdep = ints.pop()

    # ???
    ints.fromfile(f,1)
    kmfast = ints.pop()

    # Independent subunit model.
    # False for all old models (npar=nrateq=2*ncon)
    # True when npar < nrateq=2*ncon. In this case must have nsetq>0
    ints.fromfile(f,1)
    indmod = ints.pop()

    # Number of basic rates constants.
    # Normally npar=nrateq and nsetq=0, but when indmod=T then npar<nrateq.
    ints.fromfile(f,1)
    npar = ints.pop()

    # ???
    ints.fromfile(f,1)
    nsetq = ints.pop()

    # ???
    ints.fromfile(f,1)
    kstat = ints.pop()

    # Output of mechanism in characters
    # TODO clean characters
    Jch = []
    for j in range(0, jlast):
        Ich = []
        for i in range(0, ilast):  # 500 is max
             charmod = f.read(2)
             Ich.append(charmod)
        Jch.append(Ich)
    for i in range(0,ilast):
        IIch = []
        for j in range(0, jlast):
            IIch.append(Jch[j][i])
        print ''.join(IIch)

    # Read rate constants.
    irate = []
    for i in range(nrateq):
        ints.fromfile(f,1)
        irate.append(ints.pop())
    jrate = []
    for i in range(nrateq):
        ints.fromfile(f,1)
        jrate.append(ints.pop())
    QT = np.zeros((k, k), 'float64')
    for i in range(nrateq):
        doubles.fromfile(f, 1)
        QT[irate[i]-1, jrate[i]-1] = doubles.pop()
    ratename = []
    for i in range(npar):
        ratename.append(f.read(10))
        #print ratename[i], "QT[",irate[i],",",jrate[i],"]=", QT[irate[i]-1,jrate[i]-1]

    # Read ligand name and ligand molecules bound in each state.
    for j in range(0, nlig):
        ligname = f.read(20)
        #print "Number of ligand %s molecules bound to states:" %ligname
    nbound = np.zeros((nlig,k), 'int32')
    for i in range(nlig):
        for j in range(k):
            ints.fromfile(f, 1)
            nbound[i,j] = ints.pop()
        #print "to state",j+1,":",nbound[i,j]

    # Read concentration dependent rates.
    # from state
    ix = []
    for i in range(0, ncdep):
        ints.fromfile(f,1)
        ix.append(ints.pop())
    # to state
    jx = []
    for j in range(0, ncdep):
        ints.fromfile(f,1)
        jx.append(ints.pop())
        #if verbose: print "jx[",j,"]=",jx[j]
    # ligand bound in that particular transition
    il = []
    for i in range(0, ncdep):
        ints.fromfile(f,1)
        il.append(ints.pop())
        #if verbose: print "il[", i, "]=", il[i]

    # Read open state conductance.
    dgamma = []
    for j in range(0, kA):
        doubles.fromfile(f,1)
        dgamma.append(doubles.pop())

    # Get number of states in each cycle and connections.
    nsc = np.zeros(50, 'int32')
    for i in range(0, ncyc):
        ints.fromfile(f,1)
        nsc[i] = ints.pop()
    #print "nsc[", i, "]=", nsc[i]
    im = np.zeros((50, 100), 'int32')
    for i in range(0, ncyc):
        for j in range(0, nsc[i]):
            ints.fromfile(f,1)
            im[i, j] = ints.pop()
            #print "im[",i,",",j,"]=",im[i,j]
    jm = np.zeros((50,100), 'int32')
    for i in range(0, ncyc):
        for j in range(0, nsc[i]):
            ints.fromfile(f,1)
            jm[i,j] = ints.pop()
            #print "jm[",i,",",j,"]=",jm[i,j]

    # Read voltage dependent rates.
    # from state
    iv = []
    for i in range(0, nvdep):
        ints.fromfile(f,1)
        iv.append(ints.pop())
        #print "iv[",i,"]=",iv[i]
    # to state
    jv = []
    for j in range(0, nvdep):
        ints.fromfile(f,1)
        jv.append(ints.pop())
        #print "jv[", j,"]=",jv[j]

    hpar = []
    for i in range(0, nvdep):
        floats.fromfile(f,1)
        hpar.append(floats.pop())
        #print "hpar[",i,"]=",hpar[i]

    pstar = []
    for j in range(0, 4):
        floats.fromfile(f,1)
        pstar.append(floats.pop())
        #print "pstar[",j,"]=",pstar[j]

    kmcon = []
    for i in range(0, 9):
        ints.fromfile(f,1)
        kmcon.append(ints.pop())
        #print "kmcon[",i,"]=",kmcon[i]

    ieq = []
    for i in range(0, nsetq):
        ints.fromfile(f,1)
        ieq.append(ints.pop())
        #print "ieq[",i,"]=",ieq[i]

    jeq = []
    for j in range(0, nsetq):
        ints.fromfile(f,1)
        jeq.append(ints.pop())
        #print "jeq[", j, "]=", jeq[j]

    ifq = []
    for i in range(0,nsetq):
        ints.fromfile(f,1)
        ifq.append(ints.pop())
        #print "ifq[",i,"]=",ifq[i]

    jfq = []
    for j in range(0, nsetq):
        ints.fromfile(f,1)
        jfq.append(ints.pop())
        #print "jfq[",j,"]=",jfq[j]

    efacq = []
    for i in range(0, nsetq):
        floats.fromfile(f,1)
        efacq.append(floats.pop())
        #print "efacq[",i,"]=",efacq[i]

    statenames = []
    for i in range(0, kstat):
        statename = f.read(10)
        statenames.append(statename)
        #print "State name:", statename
    print "\n"

    ints.fromfile(f,1)
    nsub = ints.pop()
    ints.fromfile(f,1)
    kstat0 = ints.pop()
    ints.fromfile(f,1)
    npar0 = ints.pop()
    ints.fromfile(f,1)
    kcon = ints.pop()
    ints.fromfile(f,1)
    npar1 = ints.pop()
    ints.fromfile(f,1)
    ncyc0 = ints.pop()

    f.close()

    StateList = []
    j = 0
    for i in range(kA):
        StateList.append(mec.State(j+1, 'A', statenames[j], dgamma[j]))
        j +=1
    for i in range(kB):
        StateList.append(mec.State(j+1, 'B', statenames[j], 0))
        j +=1
    for i in range(kC):
        StateList.append(mec.State(j+1, 'C', statenames[j], 0))
        j +=1
    for i in range(kD):
        StateList.append(mec.State(j+1, 'D', statenames[j], 0))
        j +=1

    RateList = []
    for i in range(nrateq):
        cdep = False
        bound = None
        for j in range(ncdep):
            if ix[j] == irate[i] and jx[j] == jrate[i]:
                cdep = True
                bound = 'c'
        rate = QT[irate[i] - 1, jrate[i] - 1]
        RateList.append(mec.Rate(rate, irate[i], jrate[i], name=ratename[i], eff=bound))

    return mec.Mechanism(RateList, StateList, ncyc=ncyc)
    