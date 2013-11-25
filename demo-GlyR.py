import time, math, sys, socket, os
import numpy as np
from scipy.optimize import minimize

from dcpyps import dcio
from dcpyps import dataset
from dcpyps import mechanism
from dcprogs.likelihood import Log10Likelihood

str1 = "DC_PyPs: Q matrix calculations.\n"
str2 = ("Date and time of analysis: %4d/%02d/%02d %02d:%02d:%02d\n"
    %time.localtime()[0:6])
machine = socket.gethostname()
system = sys.platform
str3 = "Machine: %s; System: %s\n" %(machine, system)

# LOAD DATA.
scnfiles = [["./dcpyps/samples/glydemo/A-10.scn"], ["./dcpyps/samples/glydemo/B-30.scn"],
    ["./dcpyps/samples/glydemo/C-100.scn"], ["./dcpyps/samples/glydemo/D-1000.scn"]]
tres = [0.000030, 0.000030, 0.000030, 0.000030]
tcrit = [0.004, -1, -0.06, -0.02]
chs = [True, False, False, False]
conc = [10e-6, 30e-6, 100e-6, 1000e-6]

recs = []
bursts = []
for i in range(len(scnfiles)):
    rec = dataset.SCRecord(scnfiles[i], conc[i], tres[i], tcrit[i], chs[i])
    rec.record_type = 'recorded'
    recs.append(rec)
    bursts.append(rec.bursts)
    rec.printout()

# LOAD FLIP MECHANISM USED Burzomato et al 2004
mecfn = "./dcpyps/samples/mec/demomec.mec"
version, meclist, max_mecnum = dcio.mec_get_list(mecfn)
mec = dcio.mec_load(mecfn, meclist[2][0])

# PREPARE RATE CONSTANTS.
rates = [5000.0, 500.0, 2700.0, 2000.0, 800.0, 15000.0, 300.0, 0.1200E+06, 6000.0, 0.4500E+09, 1500.0, 12000.0, 4000.0, 0.9000E+09, 7500.0, 1200.0, 3000.0, 0.4500E+07, 2000.0, 0.9000E+07, 1000, 0.135000E+08]
mec.set_rateconstants(rates)

# Fixed rates.
#fixed = np.array([False, False, False, False, False, False, False, True,
#    False, False, False, False, False, False])
#if fixed.size == len(mec.Rates):
for i in range(len(mec.Rates)):
    mec.Rates[i].fixed = False

# Constrained rates.
mec.Rates[21].is_constrained = True
mec.Rates[21].constrain_func = mechanism.constrain_rate_multiple
mec.Rates[21].constrain_args = [17, 3]
mec.Rates[19].is_constrained = True
mec.Rates[19].constrain_func = mechanism.constrain_rate_multiple
mec.Rates[19].constrain_args = [17, 2]
mec.Rates[16].is_constrained = True
mec.Rates[16].constrain_func = mechanism.constrain_rate_multiple
mec.Rates[16].constrain_args = [20, 3]
mec.Rates[18].is_constrained = True
mec.Rates[18].constrain_func = mechanism.constrain_rate_multiple
mec.Rates[18].constrain_args = [20, 2]
mec.Rates[8].is_constrained = True
mec.Rates[8].constrain_func = mechanism.constrain_rate_multiple
mec.Rates[8].constrain_args = [12, 1.5]
mec.Rates[13].is_constrained = True
mec.Rates[13].constrain_func = mechanism.constrain_rate_multiple
mec.Rates[13].constrain_args = [9, 2]
mec.update_constrains()

mec.set_mr(True, 7, 0)
mec.set_mr(True, 15, 1)

mec.printout(sys.stdout)
theta = np.log(mec.theta())

kwargs = {'nmax': 2, 'xtol': 1e-12, 'rtol': 1e-12, 'itermax': 100,
    'lower_bound': -1e6, 'upper_bound': 0}
likelihood = []

for i in range(len(recs)):
    likelihood.append(Log10Likelihood(bursts[i], mec.kA,
        recs[i].tres, recs[i].tcrit, **kwargs))

#for i in range(len(conc)):
#    likelihood.append(Log10Likelihood(bursts[i], mec.kA, tres[i], tcrit[i], **kwargs))

def dcprogslik(x, args=None):
    mec.theta_unsqueeze(np.exp(x))
    lik = 0
    for i in range(len(conc)):
        mec.set_eff('c', conc[i])
        lik += -likelihood[i](mec.Q) * math.log(10)
    return lik

iternum = 0
def printiter(theta):
    global iternum
    iternum += 1
    lik = dcprogslik(theta)
    print("iteration # {0:d}; log-lik = {1:.6f}".format(iternum, -lik))
    print(np.exp(theta))

lik = dcprogslik(theta)
print ("\nStarting likelihood (DCprogs)= {0:.6f}".format(-lik))

start = time.clock()

success = False
result = None
while not success:
    #res = minimize(dcprogslik, np.log(theta), method='Powell', callback=printit, options={'maxiter': 5000, 'disp': True})
    result = minimize(dcprogslik, theta, method='Nelder-Mead', callback=printiter,
        options={'xtol':1e-4, 'ftol':1e-4, 'maxiter': 5000, 'maxfev': 10000,
        'disp': True})
    if result.success:
        success = True
    else:
        theta = result.x

#result = minimize(dcprogslik, theta, method='Nelder-Mead', callback=printiter,
#    options={'xtol':1e-1, 'ftol':1e-1, 'maxiter': 5000, 'maxfev': 10000,
#    'disp': True})
print ("\nDCPROGS Fitting finished: %4d/%02d/%02d %02d:%02d:%02d\n"
        %time.localtime()[0:6])
print 'time in simplex=', time.clock() - start
print '\n\nresult='
print result

print ('\n Final log-likelihood = {0:.6f}'.format(-result.fun))
print ('\n Number of iterations = {0:d}'.format(result.nit))
print ('\n Number of evaluations = {0:d}'.format(result.nfev))
mec.theta_unsqueeze(np.exp(result.x))
print "\n Final rate constants:"
mec.printout(sys.stdout)
print '\n\n'


open_pdfs = []
shut_pdfs = []
for i in range(len(scnfiles)):
    op_filename = scnfiles[i][0][:-4] + '_open.png'
    sh_filename = scnfiles[i][0][:-4] + '_shut.png'
    open_pdfs.append(dcio.png_save_pdf_fig(op_filename, recs[i].opint, mec, conc[i], tres[i], 'open'))
    shut_pdfs.append(dcio.png_save_pdf_fig(sh_filename, recs[i].shint, mec, conc[i], tres[i], 'shut'))


htmlstr = ("""<html>
    <p>HJCFIT: Fit of model to open-shut times with missed events
    (Uses HJC distributions, exact for first two deadtimes then asymptotic, to calculate likelihood of record)</p>""" +
    '<p>'+ str2 + '<p></p>' + str3 + """</p></html>""" )

htmlfile = mecfn[:-4] + '.html'
f = open(htmlfile, 'w')
f.write(htmlstr)
for i in range(len(scnfiles)):
    f.write("<p>{0} _____________________________________ {1}</p>".format(open_pdfs[i], shut_pdfs[i]))
    f.write("<img src={0} width='450' height='300'><img src={1} width='450' height='300'>".format(os.path.abspath(open_pdfs[i]), os.path.abspath(shut_pdfs[i])))

#mec.printout(f)
f.close()





""" Represents the optimization result.
    Attributes
    ----------
    x : ndarray
        The solution of the optimization.
    success : bool
        Whether or not the optimizer exited successfully.
    status : int
        Termination status of the optimizer. Its value depends on the
        underlying solver. Refer to `message` for details.
    message : str
        Description of the cause of the termination.
    fun, jac, hess : ndarray
        Values of objective function, Jacobian and Hessian (if available).
    nfev, njev, nhev : int
        Number of evaluations of the objective functions and of its
        Jacobian and Hessian.
    nit : int
        Number of iterations performed by the optimizer.
    maxcv : float
        The maximum constraint violation.
    """