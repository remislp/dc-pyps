"""A collection of functions for open probability, Popen, or dose-response
curve calculations.
"""

import sys
import math

import numpy as np

import qmatlib as qml
import scalcslib as scl

def popen(mec, tres, conc, eff='c'):
    """
    Calculate equilibrium open probability (Popen) and correct for
    unresolved blockages in case of presence of fast pore blocker.

    Parameters
    ----------
    mec : dcpyps.Mechanism
        The mechanism to be analysed.
    tres : float
        Time resolution (dead time).
    conc : float
        Concentration.

    Returns
    -------
    Popen : float
        Open probability value at a given concentration.
    """

    mec.set_eff(eff, conc)
    if tres == 0:
        p = qml.pinf(mec.Q)
        Popen = np.sum(p[:mec.kA])
#        Popen = 0
#        for i in range(mec.kA):
#            Popen = Popen + p[i]
    else:
        hmopen = scl.hjc_mean_time(mec, tres, True)
        hmshut = scl.hjc_mean_time(mec, tres, False)
        Popen = (hmopen / (hmopen + hmshut))
    if mec.fastblk:
        Popen = Popen / (1 + conc / mec.KBlk)
    return Popen

def get_P0(mec, tres, eff='c'):
    """
    Find Popen at concentration = 0.

    Parameters
    ----------
    mec : instance of type Mechanism
    tres : float
        Time resolution (dead time).

    Returns
    -------
    P0 : float
        Open probability in absence of effector.
    """

    conc = 0
    P0 = 0
    Popen = popen(mec, 0, conc)
    if Popen < 1e-10:
        P0 = Popen
    else:
        P0 = popen(mec, tres, conc)
    return P0

def get_maxPopen(mec, tres, eff='c'):
    """
    Estimate numerically maximum equilibrium open probability.
    In case Popen curve goes through a maximum, the peak open
    probability is returned.

    Parameters
    ----------
    mec : instance of type Mechanism
    tres : float
        Time resolution (dead time).

    Returns
    -------
    maxPopen : float
        Maximum equilibrium open probability.
    conc : float
        Concentration at which Popen curve reaches maximal value.
    """

    decline = get_decline(mec, tres)
    flat = False
    monot = True

    conc = 1e-9    # start at 1 nM
    Poplast = popen(mec, tres, conc)
    fac = math.sqrt(10)
    c1 = 0
    c2 = 0

    niter = 0
    while (not flat and conc < 100 and monot):
        conc = conc * fac
        Popen = popen(mec, tres, conc)
        if decline and (math.fabs(Popen) < 1e-12):
            flat = math.fabs(Poplast) < 1e-12
        else:
            rel = (Popen - Poplast) / Popen
            if niter > 1 and Popen > 1e-5:
                if (rel * rellast) < -1e-10: # goes through min/max
                    monot = False
                    c1 = conc / fac     # conc before max
                    c2 = conc    # conc after max
                flat = ((math.fabs(rel) < 1e-5) and
                    (math.fabs(rellast) < 1e-5))
            if conc < 0.01:    # do not leave before 10 mM ?
                flat = False
            rellast = rel
        Poplast = Popen
        niter += 1

    if not monot:    # find maxPopen and cmax more accurately
        epsc =  c1 / 1000    # accuracy in concentration
        epsy = 0.0001    # accuracy in open probability
        Perr = 2 * epsy
        fac = 1.01
        maxnstep  = int(math.log10(math.fabs(c1 - c2) / epsc) / math.log10(2) + 0.5)
        nstep = 0
        while nstep <= maxnstep and math.fabs(Perr) > 0:
            conc = 0.5 * (c1 + c2)
            conc1 = conc / fac
            P1 = popen(mec, tres, conc)
            conc1 = conc * fac
            P2 = popen(mec, tres, conc)
            Perr = P2 - P1
            if Perr < 0:
                c1 = conc1
            else:
                c2 = conc1

    maxPopen = popen(mec, tres, conc)
    return maxPopen, conc

def get_decline(mec, tres, eff='c'):
    """
    Find whether open probability curve increases or decreases
    with ligand concentration. Popen may decrease if ligand is inhibitor.

    Parameters
    ----------
    mec : instance of type Mechanism
    tres : float
        Time resolution (dead time).

    Returns
    -------
    decline : bool
        True if Popen curve dectreases with concentration.
    """

    Popen = popen(mec, tres, 1)    # Popen at 1 M
    P0 = get_P0(mec, tres)    # Popen at 0 M
    decline = (Popen < P0)
    return decline

def get_EC50(mec, tres, eff='c'):
    """
    Estimate numerically the equilibrium EC50 for a specified mechanism.
    If monotonic this is unambiguous. If not monotonic then returned is
    a concentration for 50% of  the peak response to the left of the peak.

    Parameters
    ----------
    mec : instance of type Mechanism
    tres : float
        Time resolution (dead time).

    Returns
    -------
    EC50 : float
        Concentration at which Popen is 50% of its maximal value.
    """

    P0 = get_P0(mec, tres)
    maxPopen, cmax = get_maxPopen(mec, tres)

    c1 = 0
    c2 = cmax
    conc = 0
    epsy = 0.001    # accuracy in Popen
    Perr = 2 * epsy
    epsc = 0.1e-9    # accuracy in concentration 0.1 nM
    nstepmax = int(math.log10(math.fabs(c1 - c2) / epsc) / math.log10(2) + 0.5)
    nstep = 0

    while math.fabs(Perr) > epsy and nstep <= nstepmax:
        nstep += 1
        conc = (c1 + c2) / 2
        Popen = popen(mec, tres, conc)
        Popen = math.fabs((Popen - P0) / (maxPopen - P0))
        Perr = Popen - 0.5
        if Perr < 0:
            c1 = conc
        elif Perr > 0:
            c2 = conc
    EC50 = conc

    return EC50

def get_nH(mec, tres, eff='c'):
    """
    Calculate Hill slope, nH, at EC50 of a calculated Popen curve.
    This is Python implementation of DCPROGS HJC_HILL.FOR subroutine.

    Parameters
    ----------
    mec : instance of type Mechanism
    tres : float
        Time resolution (dead time).

    Returns
    -------
    nH : float
        Hill slope.
    """

    P0 = get_P0(mec, tres)
    Pmax, cmax = get_maxPopen(mec, tres)
    EC50 = get_EC50(mec, tres)
    decline = get_decline(mec, tres)
    if decline:
        temp = P0
        P0 = Pmax
        Pmax = temp

    # Calculate Popen curve
    n = 64
    dc = (math.log10(EC50 * 1.1) - math.log10(EC50 * 0.9)) / (n - 1)
    c = np.zeros(n)
    y = np.zeros(n)
    for i in range(n):
        c[i] = (EC50 * 0.9) * pow(10, i * dc)
        y[i] = popen(mec, tres, c[i])

    # Find two points around EC50.
    i50 = 0
    s1 = 0
    s2 = 0
    i = 0
    while i50 ==0 and i < n-1:
        if (c[i] <= EC50) and (c[i+1] >= EC50):
            i50 = i
            y1 = math.log10(math.fabs((y[i] - P0) / (Pmax - y[i])))
            y2 = math.log10(math.fabs((y[i+1] - P0) / (Pmax - y[i+1])))
            s1 = (y2 - y1) / (math.log10(c[i+1]) - math.log10(c[i]))
            y3 = math.log10(math.fabs((y[i+1] - P0) / (Pmax - y[i+1])))
            y4 = math.log10(math.fabs((y[i+2] - P0) / (Pmax - y[i+2])))
            s2 = (y4 - y3) / (math.log10(c[i+2]) - math.log10(c[i+1]))
        i += 1

    # Interpolate linearly for Hill slope at EC50
    b = (s2 - s1) / (c[i50+1] - c[i50])
    nH = s1 + b * (EC50 - c[i50])
    return nH


def printout(mec, tres, output=sys.stdout, eff='c'):
    """
    """

    # Calculate EC50, nH and maxPopen for Popen curve
    # corrected for missed events.
    emaxPopen, econc = get_maxPopen(mec, tres)
    eEC50 = get_EC50(mec, tres)
    enH = get_nH(mec, tres)
    output.write('\n\nHJC Popen curve:\nmaxPopen = {0:.3f}; '
        .format(emaxPopen) + ' EC50 = {0:.3f} mikroM; '
        .format(eEC50 * 1000000) + ' nH = {0:.3f}'.format(enH))

    # Calculate EC50, nH and maxPopen for ideal Popen curve.
    imaxPopen, iconc = get_maxPopen(mec, 0)
    iEC50 = get_EC50(mec, 0)
    inH = get_nH(mec, 0)
    output.write('\n\nIdeal Popen curve:\nmaxPopen = {0:.3f}; '
        .format(imaxPopen) + ' EC50 = {0:.3f} mikroM; '
        .format(iEC50 * 1000000) + ' nH = {0:.3f}'.format(inH))
