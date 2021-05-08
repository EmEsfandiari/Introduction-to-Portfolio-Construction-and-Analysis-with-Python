import pandas as pd
def drawdown(return_series: pd.Series):
    """"
    Takes a time-series of asset returns
    Computes and returns a DataFrame that contains:
    the wealth index
    the previous peaks
    percent drawdowns
    """
    wealth_index = 1000*(return_series+1).cumprod()
    previous_peaks = wealth_index.cummax()
    drawdowns = (wealth_index - previous_peaks)/previous_peaks
    return pd.DataFrame({
        'Wealth': wealth_index,
        'Peaks': previous_peaks,
        'Drawdown':drawdowns
    })
 
    
    
def get_ffme_returns():
    """
    Load the Fama_French Dataset for the returns of the Top and Bottom Deciles by MarketCap
    """
    me_n = pd.read_csv('MyOwn/Portfolios_Formed_on_ME_monthly_EW.csv',header = 0, index_col = 0, na_values = -99.99)
    rets = me_n[['Lo 30','Hi 30']]
    rets.columns = ['SmallCap 30', 'LargeCap 30']
    rets = rets/100
    rets.index = pd.to_datetime(rets.index, format="%Y%m").to_period("M")
    return rets



def get_hfi_returns():
    """
    Load and format the EDHEC Hedge Fund Index Returns
    """
    hfi = pd.read_csv('edhec-hedgefundindices.csv',header = 0, index_col = 0, na_values = -99.99, parse_dates=True)
    hfi = hfi/100
    hfi.index = hfi.index.to_period("M")
    return hfi



def get_ind_returns():
    """
    Load and format the Ken French 30 Industry Portfolios Value Weighted Monthly Returns
    """
    ind = pd.read_csv('ind30_m_vw_rets.csv',header=0,index_col=0, parse_dates=True)/100
    ind.index = pd.to_datetime(ind.index,format ='%Y%m').to_period('M')
    ind.columns = ind.columns.str.strip()
    return ind



def semideviation (r):
    """
    Returns the semideviation aka negative semideviation of r 
    r must be a Series or a DataFrame
    """
    is_negative = r<0
    return r[is_negative].std(ddof=0)



def skewness (r):
    """
    Alternative to scipy.stats.skew()
    Compute the skewness of the supplied Series or DataFrame
    Returns a float or a Series
    """
    demeaned_r = r - r.mean()
    # use the population standard deviation, so set dof=0
    sigma_r = r.std(ddof=0)
    exp = (demeaned_r**3).mean()
    return exp/sigma_r**3



def kurtosis (r):
    """
    Alternative to scipy.stats.kurtosis()
    Compute the kurtosis of the supplied Series or DataFrame
    Returns a float or a Series
    """
    demeaned_r = r - r.mean()
    # use the population standard deviation, so set dof=0
    sigma_r = r.std(ddof=0)
    exp = (demeaned_r**4).mean()
    return exp/sigma_r**4



import scipy.stats
def is_normal(r, level=0.01):
    """
    Applies the Jarque-Bera test to determine if a Series is normal or not
    Test is applied at the 1% level by default
    Returns True if the hypothesis of normally is accepted,False otherwise
    """
    statistic, p_value = scipy.stats.jarque_bera(r)
    return p_value >level



def var_historic(r,level = 5):
    """
    Returns the historic Value at Risk at a specified level
    i.e. returns the number such that "level" percent of the returns fall below that number, and the (100-level) percent are above
    """
    import numpy as np
    if isinstance(r,pd.DataFrame): 
        return r.aggregate(var_historic, level = level)
    elif isinstance(r,pd.Series):
        return -np.percentile(r,level)
    else: 
        raise TypeError("Expected to be a Series or DataFrame")
        
        
        
from scipy.stats import norm
def var_gaussian(r,level = 5,modified = False):
    """
    Returns the parametric Gaussian VaR of a Series or a DataFrame
    If "modified"  is True, then the modified VaR is returned, using the Cornish-Fisher modification
    """
    # Compute the Z score assuming it was Gaussian
    z = norm.ppf(level/100)
    if modified:
        # modify the Z score based on the observed skewness and kurtosis
        s= skewness(r)
        k= kurtosis(r)
        z= (z + 
           (z**2 - 1)*s/6 +
           (z**3 - 3*z)*(k-3)/24 -
            (2*z**3 - 5*z)*(s**2)/36
           )
    return -(r.mean() + z * r.std(ddof=0))



def cvar_historic(r,level = 5):
    """
    Computes the Conditional VaR of Series or DataFrame
    """
    import numpy as np
    if isinstance(r,pd.Series): 
        is_beyond = r <= -var_historic(r, level=level)
        return -r[is_beyond].mean()
        return -r.aggregate(var_historic, level = level)
    elif isinstance(r,pd.DataFrame):
        return r.aggregate(cvar_historic, level = level)
    else: 
        raise TypeError("Expected r to be a Series or DataFrame")

        
        
def annualize_rets(r, periods_per_year):
    """
    Annualizes a set of returns
    We should infer the period per year 
    but that is currently left as an exercise for the reader
    """
    compounded_growth = (1+r).prod()
    n_periods = r.shape[0]
    return compounded_growth**(periods_per_year/n_periods)-1

        

def annualized_vol(r,periods_per_year):
    """
    Annualizes the vol of a set of returns
    We should infer the periods per year
    but that is currently left as an execise to the reader
    """
    return r.std()*(periods_per_year**0.5)



def sharpe_ratio(r,riskfree_rate, periods_per_year):
    """
    Computes the annualized sharpe ratio of a set of returns
    """
    # convert the annual risk free rate to per period
    rf_per_period = (1+riskfree_rate)**(1/periods_per_year)-1
    excess_ret = r-rf_per_period
    ann_ex_ret = annualize_rets(excess_ret,periods_per_year)
    ann_vol = annualized_vol(r,periods_per_year)
    return ann_ex_ret/ann_vol



def portfolio_ret(weights,returns):
    """
    Weights -> Returns
    """
    return weights.T @ returns # @ indicates matrix multiplication



def portfolio_vol(weights,covmat):
    """
    Weights -> Volatility
    """
    return (weights.T @ covmat @ weights )**0.5


import numpy as np
def plot_ef2(n_points, er, cov, style = ".-"):
    """
    Plots the 2-asset efficient frontier
    """
    if er.shape[0] != 2 or cov.shape[0] != 2:
        raise ValueError("plot_ef2 can only plot two asset frontiers")
    weights = [np.array([w,1-w]) for w in np.linspace(0,1,n_points)]
    rets = [portfolio_ret(w,er) for w in weights]
    vols = [portfolio_vol(w,cov) for w in weights]
    ef = pd.DataFrame({
        "Returns": rets,
        "Volatility": vols
    })
    return ef.plot.line(x = "Volatility", y = "Returns", style = style)