"""Fixed-stage regressions; seller-clustered uncertainty."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import t as tdist

def fit_model(label, data, high=100, fe=False, equal_seller=False, absolute=False):
    s=data[data.slr_hist.lt(10)|data.slr_hist.ge(high)].copy()
    xvar='buyer_abs' if absolute else 'gamma_buyer'
    yvar='seller_abs' if absolute else 'gamma_seller'
    x=pd.DataFrame({'const':1.0, 'buyer_concession':s[xvar],
        'experienced':s.slr_hist.ge(high).astype(float)},index=s.index)
    x['interaction']=x.buyer_concession*x.experienced
    x['log_buyer_experience']=np.log1p(s.byr_hist)
    x['log_initial_seller_price']=np.log(s.p2)
    x['gap_before_buyer_concession']=s.gap_before
    months=pd.get_dummies(s.month,prefix='month',drop_first=True,dtype=float)
    x=pd.concat([x,months],axis=1)
    y=s[yvar]
    ids=s.anon_slr_id
    if fe:
        x=x-x.groupby(ids).transform('mean')
        y=y-y.groupby(ids).transform('mean')
        x=x.loc[:,x.abs().max().gt(1e-12)]
    weights=1/s.groupby('anon_slr_id').anon_slr_id.transform('size') if equal_seller else np.ones(len(s))
    model=sm.WLS(y,x,weights=weights).fit(cov_type='cluster',cov_kwds={'groups':ids,'use_correction':True},use_t=True)
    nclusters=int(ids.nunique())
    # Within estimation absorbs seller intercepts; replace the ordinary CR1
    # residual-df factor with one counting the absorbed seller effects.
    if fe:
        rank=int(np.linalg.matrix_rank(x.to_numpy()))
        absorbed=nclusters
        factor=(len(s)-rank)/(len(s)-rank-absorbed)
        model.cov_params_default *= factor
        model._cache.clear()
    cov=model.cov_params()
    def contrast(terms):
        w=pd.Series(0.0,index=model.params.index)
        for k,v in terms.items():w[k]=v
        b=float(w@model.params)
        se=float(np.sqrt(w@cov@w))
        crit=float(tdist.ppf(.975,nclusters-1))
        pval=float(2*tdist.sf(abs(b/se),nclusters-1))
        return {'estimate':b,'se':se,'ci_low':b-crit*se,'ci_high':b+crit*se,'p':pval}
    rec={'model':label,'n':len(s),'sellers':nclusters,'threshold':high,
         'novice_n':int(s.slr_hist.lt(10).sum()),
         'experienced_n':int(s.slr_hist.ge(high).sum()),
         'novice_sellers':int(s.loc[s.slr_hist.lt(10),'anon_slr_id'].nunique()),
         'experienced_sellers':int(s.loc[s.slr_hist.ge(high),'anon_slr_id'].nunique()),
         'seller_fe':fe,'equal_seller_weight':equal_seller,'absolute_scale':absolute}
    for name,terms in [('novice_slope',{'buyer_concession':1}),
                       ('experienced_slope',{'buyer_concession':1,'interaction':1}),
                       ('slope_difference',{'interaction':1})]:
        rec.update({f'{name}_{key}':val for key,val in contrast(terms).items()})
    coefficients=[{'model':label,'term':term,'coefficient':float(model.params[term]),
                   'cluster_se':float(model.bse[term])} for term in model.params.index]
    return rec, coefficients
