"""Generate one self-contained LaTeX report; graphs/data/references are inline."""
from pathlib import Path
import argparse,json,math
ROOT=Path(__file__).resolve().parent.parent
def esc(s):
    for old,new in [('&',r'\&'),('%',r'\%'),('$',r'\$'),('#',r'\#'),('_',r'\_')]:s=str(s).replace(old,new)
    return s
def f(x,n=4):return f'{float(x):.{n}f}'
def count(n):return f'{int(n):,}'
def pvalue(n):return '$<0.001$' if n<.001 else f(n,3)
def rows_table(rows,spec,headers,caption,label,notes=''):
    return '\\begin{table}[htbp]\n\\centering\\small\n\\caption{'+caption+'}\\label{'+label+'}\n\\begin{tabular}{'+spec+'}\n\\toprule\n'+headers+' \\\\\n\\midrule\n'+'\n'.join(' & '.join(r)+' \\\\' for r in rows)+'\n\\bottomrule\n\\end{tabular}\n'+(r'\par\vspace{4pt}\begin{minipage}{\linewidth}\footnotesize '+notes+r'\end{minipage}' if notes else '')+'\n\\end{table}\n'
def longtable(rows,spec,headers,caption,label):
    return '\\small\n\\begin{longtable}{'+spec+'}\n\\caption{'+caption+'}\\label{'+label+'}\\\\\n\\toprule\n'+headers+' \\\\\n\\midrule\\endfirsthead\n\\toprule\n'+headers+' \\\\\n\\midrule\\endhead\n\\bottomrule\\endfoot\n'+'\n'.join(' & '.join(r)+' \\\\' for r in rows)+'\n\\end{longtable}\n\\normalsize\n'
def interval_plot(models,width,height,scale=10,kind='interaction',names=None,xlabel=None,xlim=None):
    prefix='slope_difference_' if kind=='interaction' else ''
    est='estimate' if kind=='interaction' else 'slope'
    vals=[]
    labels=[]
    for i,m in enumerate(models):
        x=float(m[prefix+est])*scale
        err=(float(m[prefix+'ci_high'])-float(m[prefix+'ci_low']))/2*scale
        vals.append(f'{x:.8f} {len(models)-i} {err:.8f} \\\\')
        labels.append(esc(names[i] if names else m.get('sample',m.get('model',''))))
    lo=min((m[prefix+'ci_low']*scale for m in models),default=-1);hi=max((m[prefix+'ci_high']*scale for m in models),default=1)
    span=hi-lo;lo=min(0,lo)-.1*span;hi=max(0,hi)+.1*span
    if xlim:lo,hi=xlim
    ticks=','.join(str(n) for n in range(len(models),0,-1))
    lab=','.join('{'+l+'}' for l in labels)
    tickstyle=r'scaled x ticks=false,xticklabel style={/pgf/number format/fixed},'
    if xlim:tickstyle+=r'xtick={-.15,-.075,0,.075,.15},xticklabel style={font=\scriptsize,/pgf/number format/fixed, /pgf/number format/precision=3},'
    return r'\begin{tikzpicture}\begin{axis}['+f'width={width},height={height},xmin={lo:.6f},xmax={hi:.6f},ymin=.4,ymax={len(models)+.6},ytick={{{ticks}}},yticklabels={{{lab}}},'+r'axis lines=left,xmajorgrids=true,grid style={gray!15},tick label style={font=\small},xlabel style={font=\small},ylabel style={font=\small},'+tickstyle+('xlabel={'+xlabel+'},' if xlabel else '')+r']\addplot[gray,dashed] coordinates {(0,0)(0,'+str(len(models)+1)+r')};\addplot+[only marks,mark=*,color=navy,error bars/.cd,x dir=both,x explicit] table[x=x,y=y,x error=err,row sep=\\]{x y err \\'+'\n'+'\n'.join(vals)+r'};\end{axis}\end{tikzpicture}'
def raw_plot(data,value,ylabel,ymax):
    out=r'\begin{tikzpicture}\begin{axis}[width=.94\linewidth,height=6.0cm,xmin=0,xmax=100,ymin=0,ymax='+str(ymax)+r',xlabel={Buyer concession bin (\% of prior gap)},ylabel={'+ylabel+r'},axis lines=left,ymajorgrids=true,grid style={gray!15},tick label style={font=\small},label style={font=\small},legend style={font=\scriptsize,draw=none,at={(.5,-.25)},anchor=north,legend columns=1}]'
    for group,color,mark,name in [('0-9','rust','*','Experience count 0--9'),('100+','navy','square*','Experience count 100+')]:
        pts=' '.join(f'({(d["buyer_concession_bin"]+.5)*10:.1f},{d[value]*100:.6f})' for d in data if d['experience_group']==group)
        out+=r'\addplot[color='+color+',mark='+mark+r',thick] coordinates {'+pts+r'};\addlegendentry{'+name+'}'
    return out+r'\end{axis}\end{tikzpicture}'
def generate(z):
    models=z['primary_models'];m=models[0];meta=z['sample_metadata']
    flowrows=[[esc(x['step']),count(x['rows']),count(x['threads']),count(x['sellers'])] for x in z['sample_flow']]
    flowrows += [['Incoming qualifying buyer offers','--',count(meta['incoming_round3']),'--'],['Four-offer analysis sample','--',count(meta['main_threads']),count(meta['main_sellers'])],['Primary experience contrast','--',count(m['n']),count(m['sellers'])]]
    flow=rows_table(flowrows,'p{7.1cm}rrr','Filter / sample & Offer rows & Threads & Sellers','Sequential sample construction','tab:flow','The first six rows are sequential history filters. The last three rows select fixed-stage analytical samples. The raw prefix is nonrandom; the last seller block is removed because it may be truncated.')
    desc=rows_table([[esc(d['experience_group']),count(d['n']),count(d['sellers']),f(d['buyer_concession_mean']*100,2),f(d['seller_concession_mean']*100,2),f(d['median_initial_price'],2)] for d in z['descriptives']],'lrrrrr','Experience & Threads & Sellers & Buyer mean & Seller mean & Median $S_2$','Descriptive statistics by recorded seller experience','tab:desc','Concession means are percentages of the relevant price gap; prices use the source price units. Some sellers cross experience thresholds over time, so seller counts need not sum to the unique total. The observed minimum experience count is 1.')
    # Display focal coefficients and all controls for the three main columns.
    co={(x['model'],x['term']):x for x in z['coefficients']}
    terms=[('buyer_concession',r'Buyer concession ($\beta$)'),('experienced',r'Experienced indicator ($\theta$)'),('interaction',r'Buyer concession $\times$ experience ($\delta$)'),('log_buyer_experience','Log(1 + buyer experience)'),('log_initial_seller_price',r'Log first seller counteroffer ($S_2$)'),('gap_before_buyer_concession','Gap before buyer concession'),('const','Constant')]
    mainrows=[]
    for term,label in terms:
        values=[]
        for model in models[:3]:
            v=co[(model['model'],term)]
            values.append(r'\shortstack{'+f(v['coefficient'])+r'\\('+f(v['cluster_se'])+')}' )
        mainrows.append([label]+values)
    mainrows += [['Month fixed effects','Yes','Yes','Yes'],['Threads']+[count(x['n']) for x in models[:3]],['Seller clusters']+[count(x['sellers']) for x in models[:3]],['Interaction p-value']+[f(x['slope_difference_p'],3) for x in models[:3]]]
    main_table=rows_table(mainrows,'p{7.1cm}rrr','Variable & All & Discovery & Validation','Primary OLS interaction regressions','tab:main','Dependent variable: seller remaining-gap concession $q$. Parentheses contain seller-clustered standard errors. Reference experience count: below 10; experienced: at least 100. Counts 10--99 are excluded. Month reference: June 2012. No significance stars are used; focal p-values and intervals are reported explicitly.')
    checknames=['All sellers','Discovery','Validation','Seller fixed effects','Experience 50+','Experience 250+','No messages',r'Price $1$--$1{,}000$','Exclude midpoint / zero','Equal seller weights','Common-price scale']
    checks=rows_table([[f'M{i+1}',name,count(x['n']),f(x['slope_difference_estimate']),f(x['slope_difference_se']),f'[{f(x["slope_difference_ci_low"],3)}, {f(x["slope_difference_ci_high"],3)}]',f(x['slope_difference_p'],3)] for i,(name,x) in enumerate(zip(checknames,models))],'lp{4.0cm}rrrrr',r'ID & Specification & $N$ & $\delta$ & SE & 95\% CI & p','All eleven planned interaction specifications','tab:checks','M1--M10 use gap fractions. M11 scales both price movements by $S_2$ and estimates a different parameter. Confidence intervals are seller-clustered. None of these eleven planned interaction intervals excludes zero. The seller fixed-effects CR1 adjustment counts the absorbed seller intercepts conservatively.')
    grouprows=[]
    for i,x in enumerate(models):
        grouprows.append([f'M{i+1}',f(x['novice_slope_estimate']),f(x['novice_slope_se']),f(x['experienced_slope_estimate']),f(x['experienced_slope_se']),count(x['novice_n']),count(x['experienced_n'])])
    group_table=rows_table(grouprows,'lrrrrrr',r'ID & Novice slope & SE & Experienced slope & SE & Novice $N$ & Exp. $N$','Group-specific slopes for every planned model','tab:group',r'Model IDs are defined in Table~\ref{tab:checks}. Experienced slope equals $\beta+\delta$, with its standard error calculated using the covariance between these terms. M11 has common-price rather than gap-fraction units.')
    measures=longtable([[esc(x['measure']),esc(x['sample']),count(x['n']),f(x['slope']),f(x['se']),f'[{f(x["ci_low"],3)}, {f(x["ci_high"],3)}]',pvalue(x['p'])] for x in z['measurement_models']],'p{4.3cm}lrrrrr',r'Measure & Sample & $N$ & Slope & SE & 95\% CI & p','Exploratory common-slope measurement comparisons','tab:measure')
    more=rows_table([[esc(x['model'].replace('Exploratory common-price: ','')),count(x['n']),f(x['novice_slope_estimate']),f(x['experienced_slope_estimate']),f(x['slope_difference_estimate']),f(x['slope_difference_p'],3)] for x in z['exploratory_group_models']],'lrrrrr',r'Seller half & $N$ & Novice slope & Exp. slope & Difference & p','Exploratory common-price experience interactions','tab:extra','Discovery difference CI: $[-0.0914,0.0458]$; validation: $[0.0024,0.1716]$. No multiplicity adjustment. A marginally significant validation estimate with a different-sign discovery estimate does not establish a stable experience effect.')
    primary_fig=interval_plot(models[:3],'.90\\linewidth','6.7cm',names=['All sellers','Discovery sellers','Validation sellers'],xlabel=r'Response difference per 10 pp buyer concession (seller pp)')
    robust_fig=interval_plot(models[:10],'.88\\linewidth','10.5cm',names=checknames[:10],xlabel=r'Response difference per 10 pp buyer concession (seller pp)')
    measures_fig=''
    for j,(measure,title) in enumerate([('Remaining-gap fractions','Remaining-gap fractions'),('Price movements / S2',r'Both price movements / $S_2$')]):
        mm=[x for x in z['measurement_models'] if x['measure']==measure]
        measures_fig+=r'\begin{minipage}{.49\linewidth}\centering\small\textbf{'+title+r'}\par\vspace{4pt}'+interval_plot(mm,'.99\\linewidth','6.3cm',scale=1,kind='slope',names=['All','Discovery','Validation'],xlabel='Slope (dimensionless)',xlim=(-.19,.17))+r'\end{minipage}'+(r'\hfill' if j==0 else '')
    bins=raw_plot(z['binned_concessions'],'seller_concession',r'Mean seller concession (\%)',40)
    selection=raw_plot(z['response_selection'],'acceptance',r'Buyer offers accepted (\%)',100)
    raw_fig=r'\begin{minipage}{.49\linewidth}\centering\textbf{Continuing negotiations}\par'+bins+r'\end{minipage}\hfill\begin{minipage}{.49\linewidth}\centering\textbf{Incoming buyer offers}\par'+selection+r'\end{minipage}'
    coeffrows=[]
    ids={m['model']:f'M{i+1}' for i,m in enumerate(models)}
    for c in z['coefficients']:
        term=c['term'].replace('month_','Month ').replace('_',' ')
        coeffrows.append([ids[c['model']],esc(term),f(c['coefficient'],6),f(c['cluster_se'],6)])
    coefftable=longtable(coeffrows,'lp{8.4cm}rr','Model & Term & Coefficient & Clustered SE','Complete coefficient vectors for the planned models','tab:full')
    bindata=longtable([[esc(v['experience_group']),str(int(v['buyer_concession_bin'])*10)+'--'+str((int(v['buyer_concession_bin'])+1)*10),count(v['n']),f(v['buyer_concession']*100,3),f(v['seller_concession']*100,3)] for v in z['binned_concessions']],'llrrr',r'Experience & Buyer bin (\%) & $N$ & Mean buyer (\%) & Mean seller (\%)','Underlying raw-concession graph data','tab:bins')
    seldata=longtable([[esc(v['experience_group']),str(int(v['buyer_concession_bin'])*10)+'--'+str((int(v['buyer_concession_bin'])+1)*10),count(v['n']),f(v['buyer_concession']*100,3),f(v['acceptance']*100,3),f(v['counteroffer']*100,3)] for v in z['response_selection']],'llrrrr',r'Experience & Buyer bin (\%) & $N$ & Mean buyer (\%) & Accept (\%) & Counter (\%)','Underlying response-selection graph data','tab:selection')
    content=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=23mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath,amssymb,amsthm,booktabs,longtable,array}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usepackage{hyperref,enumitem,caption,fancyhdr}
\usepackage[section]{placeins}
\definecolor{navy}{RGB}{40,100,130}
\definecolor{rust}{RGB}{169,87,40}
\hypersetup{colorlinks=true,linkcolor=navy,urlcolor=navy,citecolor=navy,pdftitle={Bargaining Experience and Reciprocity: An eBay Pilot}}
\setlength{\parskip}{5pt}
\setlength{\parindent}{0pt}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.18}
\setlist{itemsep=2pt,topsep=4pt}
\captionsetup{font=small,labelfont=bf}
\pagestyle{fancy}\fancyhf{}\fancyhead[L]{\small Bargaining experience and reciprocity}\fancyhead[R]{\small Empirical pilot}\fancyfoot[C]{\thepage}
\setlength{\headheight}{14pt}
\newtheorem{proposition}{Proposition}
\title{\textbf{Bargaining Experience and Reciprocity}\\[5pt]\large A fixed-stage eBay pilot with seller-level validation\\and an exploratory measurement comparison}
\author{nakshatra0904}
\date{11 October 2026\quad |\quad Version 1.1}
\begin{document}
\maketitle
\begin{abstract}
I investigate whether bargaining experience changes the strength of
reciprocal concession-making, rather than only the average concession level.
Using 30,419 actual four-offer eBay Best Offer threads from 4,520 sellers in a
nonrandom public-data prefix, I estimate a fixed-stage experience-by-concession
interaction. The primary novice/experienced contrast uses 27,016 threads and
3,004 seller clusters. Its interaction is 0.0127 (clustered SE 0.0587,
95\% CI $[-0.1023,0.1277]$, p=0.829); a seller-level split and planned checks
do not establish weaker reciprocity among experienced sellers. A benchmark
response slope is positive for remaining-gap fractions, 0.090, but negative
for price movements on a common scale, $-0.097$. This exploratory sign
disagreement recurs across the seller split. An algebraic derivation shows
why these different parameters can have opposite signs. The proposed
contribution is an experience-response extension and a transparent measurement
diagnostic, not a causal effect, a refutation of the literature, or verified
publication-level novelty.
\end{abstract}
\textbf{Reading guide.} The main text explains the design and interpretation.
Tables report all planned and exploratory focal estimates. Four figures show
validation, robustness, selection and measurement sensitivity. Appendices
include every planned-model coefficient and the graph data. All numerical
outputs are consolidated in \texttt{results/results.json}; the LaTeX source
contains its figures and references inline.
\clearpage
\tableofcontents
\clearpage
\section{Research question and contribution}
Online bargaining records make it possible to observe both prices and the
offer sequence. I study the buyer's first counteroffer and the
seller's following counteroffer at the same stage across threads. The original
interest was bargaining on ride platforms; I use eBay because
the public archive supplies actual offer histories. It contains no inDrive data.

The question is: \emph{does experience change how strongly a seller responds
to an opponent's concession?} Conceding less on average and being less
responsive to a buyer's new concession are different empirical claims.

Backus, Blake, Larsen and Tadelis (2020) study reciprocity and experience-related
concession levels in eBay data. Their appendix already considers alternative
percentage-concession measures. Fong and Waisman (2025) use an instrumental-variable
design to study delay. These findings motivate my empirical question;
I do not reproduce those papers' exact samples or identification in this pilot.

\subsection{What is an extension, and what is already established?}
\begin{enumerate}
\item \textbf{Existing foundation:} reciprocal concession patterns, bargaining
experience and their relation to concession levels have been studied before.
Comparing bargaining rounds alone or checking an alternative scale alone
would not be a new contribution.
\item \textbf{Proposed extension:} interact the opponent's concession with
seller experience at one fixed stage. I distinguish slope heterogeneity from
average toughness and examine the same pre-set contrast on disjoint seller halves.
\item \textbf{Additional exploratory diagnostic:} document and explain a
measurement discrepancy within the completed pilot. The common-price check
was planned; its seller-split follow-up followed the observed disagreement.
\end{enumerate}
My targeted literature search did not establish that the exact interaction
design had already been published. This is a candidate student-project
extension; I do not claim certified global novelty. I retain the null primary
result and report all planned tests.

\section{A simple response model and testable hypothesis}
Let $x\in[0,1]$ denote the buyer's concession and $q\in[0,1]$ the seller's
following concession, each as a fraction of its relevant price gap. I use
the following illustrative reduced-form behavioral loss
\begin{equation}
L(q;e,x)=\frac{c}{2}[q-m(e)]^2+\frac{\rho(e)}{2}(q-x)^2,
\qquad c>0,\quad\rho(e)>0.\label{eq:loss}
\end{equation}
Here $m(e)$ is a preferred concession without the matching motive, and
$\rho(e)$ is the weight on matching the opponent's concession. This is an
illustrative response model, not a full alternating-offers equilibrium.
\begin{proposition}
For $m(e),x\in[0,1]$, the unique minimizer is
\[
q^*(e,x)=\frac{c\,m(e)+\rho(e)x}{c+\rho(e)}.
\]
Its response slope is positive. Holding $c$ fixed, an experience-related
decline in $\rho$ reduces that slope, whereas a decline in $m$ can reduce
concession levels without changing the slope.
\end{proposition}
\begin{proof}
The first-order condition is $c(q-m)+\rho(q-x)=0$ and the second derivative
is $c+\rho>0$. The solution is a convex combination of $m$ and $x$, so it is
feasible. Differentiation gives
\[
\frac{\partial q^*}{\partial x}=\frac{\rho(e)}{c+\rho(e)}>0,\qquad
\frac{\partial^2q^*}{\partial e\,\partial x}
=\frac{c\rho'(e)}{[c+\rho(e)]^2}.
\]
The intercept component can change through $m$ while the slope stays fixed.
\end{proof}
My directional hypothesis recorded before inspecting sample outcomes was
that experienced sellers have a weaker response slope. Observational data
cannot separately identify $c$, $m$ and $\rho$, or attribute a slope to a
reciprocity motive rather than strategic response or selection.

\section{Data and sample construction}
\subsection{Public source, period and bounded download}
I use the NBER anonymized eBay bargaining archive. I retained exactly the
first 67,108,864 compressed bytes (64 MiB) with a byte-range download.
It produced 2,234,913 offer rows, 1,324,190 thread IDs and 21,315 sellers.
Observed offer timestamps span June 2012--December 2013. The sample is a
contiguous, seller-grouped prefix, not a random or representative draw.
I discarded the final seller block because the range may end mid-history.
The download manifest records the range, source and checksum.

\subsection{History filters and the fixed stage}
I remove identical analysis-field records, inconsistent party identifiers,
conflicting timestamps, non-alternating sequences, nonpositive prices, missing
initial experience and automatic acceptance/rejection histories. Pre-terminal
offers must have the source countered status. Histories are chronologically
ordered, contain at most six offers, and require each observable interior
concession to lie between the preceding offers. These restrictions select
a subset; they are not the original paper's exact cleaning procedure.
@@FLOW@@
The fixed stage consists of four prices: $B_1$ (initial buyer offer),
$S_2$ (first seller counteroffer), $B_3$ (first buyer counteroffer), and
$S_4$ (second seller counteroffer). Define
\begin{equation}
x=\frac{B_3-B_1}{S_2-B_1},\qquad
q=\frac{S_2-S_4}{S_2-B_3},\qquad
d=\frac{S_2-B_1}{S_2}.\label{eq:measures}
\end{equation}
Qualifying histories have positive denominators and $x,q\in[0,1]$.
For illustration only, $B_1=60$, $S_2=100$, $B_3=80$, $S_4=90$ imply
$x=q=0.5$. This numerical example is not an observation used in estimation.
@@DESC@@
\subsection{Experience definition and seller split}
The codebook describes experience as previous threads, while the paper's
Table I discussion describes a count including the current thread. I use
the supplied count unchanged and label thresholds as recorded experience.
The observed minimum is 1; the pre-set novice bin is below 10 and the
experienced bin is at least 100. Counts 10--99 remain in descriptive and
common-slope analyses but are excluded from the primary contrast.
Some sellers cross thresholds over time; group seller counts therefore need
not sum to the unique total.

Before fitting, I split seller IDs by SHA-256: the integer represented by
the first eight hexadecimal digits determines the half by parity. No seller
appears in both halves. Buyers can appear in both halves, and the comparison
is a seller-level stability check, not a fully independent population experiment.

\section{Regression specifications and uncertainty}
\subsection{Primary interaction}
For the fixed-stage qualifying continuers, I estimate
\begin{equation}
q_i=\alpha+\beta x_i+\theta E_i+\delta(x_iE_i)
+X_i'\eta+\mu_{m(i)}+\varepsilon_i.\label{eq:primary}
\end{equation}
$E_i=1$ for a recorded seller count of at least 100; the reference count is
below 10. $X_i$ contains log(1 + buyer experience), log $S_2$ and $d$ before
the buyer's concession. Calendar-month effects use the initial offer month.
I implement ordinary least squares as weighted least squares with unit
weights. For the equal-seller check, I use inverse within-sample seller thread
counts. For the seller fixed-effects check, I demean within seller and absorb
seller intercepts.

The novice slope is $\beta$, the experienced slope is $\beta+\delta$, and
$\delta$ is the focal difference. Seller-clustered covariance allows correlated
errors across a seller's threads. Intervals and two-sided p-values use the
cluster-count t reference. The fixed-effects variance adjustment also counts
absorbed seller intercepts. It does not solve omitted slope heterogeneity.

\subsection{Benchmark and measurement follow-up}
I estimate the benchmark using all experience categories, continuous log(1 + seller
experience), the buyer experience/price/gap controls, and month effects.
In the measurement follow-up, I keep these controls and threads fixed but change
the exposure/outcome definitions. It includes gap fractions; both price
movements divided by $S_2$; and percentages of each party's own preceding price.
I do not claim causal identification or apply a multiplicity adjustment.

\section{Primary results and validation}
@@MAIN@@
I estimate an interaction of $0.0127$ with clustered SE $0.0587$, 95\% CI
$[-0.1023,0.1277]$ and p=0.829. A 10 percentage point larger buyer concession
therefore has an experienced-minus-novice response difference of $+0.13$
seller percentage points, with CI $[-1.02,1.28]$. The interval does not support
the proposed directional prediction, and it does not establish equivalence.

Discovery and validation estimates are $+0.0452$ and $-0.0113$, respectively;
both intervals include zero. The experience result is not stable evidence
of a stronger or weaker response.
\begin{figure}[htbp]\centering
@@PRIMARYFIG@@
\caption{Primary experience interaction and seller-level validation.
Points are adjusted slope differences expressed as the seller response in
percentage points per 10 pp buyer concession. Whiskers are 95\% seller-clustered
intervals. Source: NBER eBay, June 2012--December 2013, nonrandom prefix.}
\label{fig:primary}\end{figure}

In the all-experience benchmark, I estimate a positive gap-fraction response
slope of $0.090$ (SE $0.0176$, CI $[0.055,0.124]$). A 10 pp larger buyer
concession is associated with a 0.90 pp larger seller concession. This
resembles the published pattern but is neither an exact coefficient replication
nor evidence that a norm caused it. Raw seller concession means are 26.43\%
for novices and 23.18\% for experienced sellers. That level difference is
descriptive; it does not establish an experience difference in response slopes.

\section{Planned robustness and continuation selection}
@@CHECKS@@
@@GROUPS@@
The planned experience checks include seller fixed effects, 50+/250+
thresholds, no message threads, prices $1$--$1{,}000$, exclusion of exact
midpoints and zero concessions, equal seller weights and common-price scaling.
All eleven planned interaction intervals include zero. Dropping messages
leaves only 219 novice threads; precision depends on the small novice group,
not only on the large total sample.
\begin{figure}[htbp]\centering
@@ROBUSTFIG@@
\caption{Planned gap-fraction interaction checks. Units are seller percentage
points per 10 pp buyer concession; whiskers are 95\% seller-clustered intervals.
Common-price scaling is omitted from this figure because its units differ,
but it is reported in Tables~\ref{tab:checks} and \ref{tab:group}.
Source: NBER eBay, June 2012--December 2013.}\label{fig:robust}\end{figure}

The secondary sample contains 70,167 qualifying incoming buyer counteroffers.
Higher-concession offers are often accepted, so no next seller counteroffer
is observed. The raw binned curves show this continuation selection; they
do not correct it. The outcome is responsiveness conditional on a qualifying
continued negotiation, not an unconditional response to every buyer offer.
\begin{figure}[htbp]\centering
@@RAWFIG@@
\caption{Raw concessions and response selection. Left: mean seller remaining-gap
concession among four-offer continuers. Right: fraction of incoming buyer
round-3 offers accepted. Points are 10 pp bins; groups use recorded experience.
High-concession novice bins are sparse (only four continuing threads at
80--90\% and none at 90--100\%). Source: NBER eBay, June 2012--December 2013.}
\label{fig:selection}\end{figure}

\section{Exploratory measurement discrepancy}
Using the same 30,419 threads and benchmark controls, I find a positive slope for gap
fractions, $+0.090$ with CI $[0.055,0.124]$, and a negative slope when both
price movements are divided by $S_2$, $-0.097$ with CI $[-0.120,-0.075]$.
The validation half reproduces the sign disagreement: $+0.096$ versus $-0.088$.
These definitions estimate different parameters.
@@MEASURES@@
The published online appendix already checks own-prior-price percentage
concessions (Table D2). Under that definition this pilot's pooled estimate
is $-0.0076$ with CI $[-0.0156,0.0005]$. The prefix, controls and lack of listing
category/condition controls differ from the published specification. An
exact replication is needed before arguing that a discrepancy is substantive.
I therefore do not present alternative scaling itself as an unstudied idea.
\clearpage
\begin{figure}[htbp]\centering
@@MEASUREFIG@@
\caption{Exploratory measurement comparison on identical threads and controls.
Points are regression slopes with 95\% seller-clustered intervals. The two
panels use different parameters; signs recur in the same seller halves.
Source: NBER eBay, June 2012--December 2013, nonrandom prefix.}
\label{fig:measure}\end{figure}
@@EXTRA@@
I conducted the seller-split measurement comparison after the planned check.
I had already used the validation set for the primary test. I added the own-price
percentage diagnostic after locating the published appendix's definition. These analyses remain exploratory. In particular, the marginal
validation p-value in Table~\ref{tab:extra} has no matching discovery result
and no multiplicity correction.

\subsection{Why opposite response signs can coexist}
From Equation~\ref{eq:measures}, define common-price movements
$a=(B_3-B_1)/S_2$ and $s=(S_2-S_4)/S_2$. Then $a=dx$ and $s=d(1-x)q$.
\begin{proposition}
Holding $d>0$ and other covariates fixed, suppose
$\mathbb{E}[q\mid x,d,Z]=A+Bx$. Then
\[
\mathbb{E}[s\mid x,d,Z]=d(1-x)(A+Bx),\qquad
\frac{\partial\mathbb{E}[s\mid x,d,Z]}{\partial a}=B-A-2Bx.
\]
Consequently $B>0$ need not imply a positive common-price response.
\end{proposition}
\begin{proof}
Substitute $s=d(1-x)q$ into the conditional expectation. Differentiate with
respect to $x$ and divide by $\partial a/\partial x=d$.
\end{proof}
For example, $A=0.2$ and $B=0.1$ imply a positive gap-fraction slope but a
negative common-price derivative for every $x\in[0,1]$. These are illustrative
parameters, not fitted estimates. The identity clarifies the measurement
comparison; it does not identify motives or show that either measure is wrong.

\section{Interpretation, limits and further research}
I completed the proposed experience-response extension, but I did not find
support for its directional hypothesis. A lower average concession can coexist with a
similar estimated responsiveness. A null interaction is not a proof that
experience never matters or that the groups behave identically.

The pilot is limited by nonrandom prefix sampling, selected continuation,
observational experience, unobserved values/costs and missing listing
category/condition controls. Seller fixed effects absorb mean differences,
not endogenous experience, seller survival or unobserved response slopes.
The measurement comparison is an exploratory discrepancy requiring exact
replication of the published sample and definitions.

A stronger extension would use the full archive, join listing characteristics,
study changes within sellers while separating experience from calendar time,
and explicitly model acceptance versus counteroffering. An experiment
randomizing bargaining practice would offer stronger identification. Larger
samples improve precision but do not automatically solve these problems.

\section{Reproducibility and project organization}
My repository includes a single consolidated results file, processed
empirical data, source provenance, shared regression code, internal design
notes and a workflow for numerical verification and report compilation.
The internal plan is not an externally registered pre-analysis plan.
The repository is available at:
\begin{center}\small
\url{https://github.com/nakshatra0904/bargaining-experience-reciprocity}
\end{center}

\textbf{Reproduction:} install \texttt{requirements.txt} with Python 3.12;
run \texttt{scripts/run\_analysis.py}, then
\texttt{scripts/verify\_results.py} and \texttt{scripts/build\_report.py}.
See the README for complete commands. The supplied compact CSV uses eight
significant digits; the current reproduction agrees with the original primary
interactions within $1.9\times10^{-9}$. Across regression and descriptive outputs,
the maximum difference is $1.8\times10^{-8}$. Graph bins are recomputed from the
supplied rounded sample, which can move observations at bin boundaries. The
reference verification tolerance is $10^{-6}$.

\textbf{Compilation:} this standalone source embeds graph coordinates and
references. It requires no external figure or bibliography files. The report
can be compiled in Overleaf or with a standard two-pass pdfLaTeX build.
I compiled this PDF with hosted pdfLaTeX at TeXLive.net. Scientific output remains
in this report; all machine-readable outputs
remain in \texttt{results/results.json}.

\begin{thebibliography}{9}
\bibitem{backus} Backus, M., Blake, T., Larsen, B., and Tadelis, S. (2020).
Sequential Bargaining in the Field: Evidence from Millions of Online Bargaining
Interactions. \emph{The Quarterly Journal of Economics}, 135(3), 1319--1361.
\href{https://doi.org/10.1093/qje/qjaa003}{doi:10.1093/qje/qjaa003}.
\bibitem{appendix} Backus, M., Blake, T., Larsen, B., and Tadelis, S. (2020).
Online appendix, particularly Tables D1 and D2.
\href{https://faculty.haas.berkeley.edu/stadelis/BargainingOnlineAppendix.pdf}{Author-hosted appendix}.
\bibitem{fong} Fong, J., and Waisman, C. (2025).
The Effects of Delay in Bargaining: Evidence from eBay. \emph{Management Science}.
Published online 11 April 2025.
\href{https://doi.org/10.1287/mnsc.2023.01562}{doi:10.1287/mnsc.2023.01562}.
\bibitem{data} National Bureau of Economic Research. Public anonymized eBay
bargaining archive associated with working paper 24306.
\href{https://back.nber.org/appendix/w24306/bargaining/}{Data and codebook}.
Source download and access recorded for this October 2026 pilot.
\end{thebibliography}
\clearpage\appendix
\section{Complete planned-model coefficients}
Model identifiers M1--M11 are defined in Table~\ref{tab:checks}. All coefficients,
including month effects, are shown below; the seller fixed-effects model omits
columns with zero within-seller variation. These are the actual fitted
coefficient vectors, not hypothetical specifications.
@@COEFFICIENTS@@
\clearpage
\section{Graph inputs and sample diagnostics}
The following tables give every binned point, including the intermediate
experience group not drawn in the main two-group curves. Intervals of buyer
concessions are generated by right-closed 10 pp bins; zero is included in the
first bin. Missing bins are omitted rather than assigned zero.
@@BINDATA@@
@@SELDATA@@
\section{Source checksum and licensing scope}
The retained compressed byte range is 0--67,108,863. Its SHA-256 is
\begin{center}\small\ttfamily
c68403e3759c653ce5a1c5598a71b58d0d6ce\\
e97de3d0205635a7dd7fff25285
\end{center}
The source-reported compressed total is 1,374,076,192 bytes. The project
retains complete CSV lines from the prefix and removes the final seller.
The repository records separate hashes of the delivered processed files.
The MIT license covers original code and report text, not the eBay/NBER data,
source codebook or cited publications. Source-provider terms remain applicable.
\end{document}
'''
    blocks={'FLOW':flow,'DESC':desc,'MAIN':main_table,'CHECKS':checks,'GROUPS':group_table,'PRIMARYFIG':primary_fig,'ROBUSTFIG':robust_fig,'RAWFIG':raw_fig,'MEASURES':measures,'MEASUREFIG':measures_fig,'EXTRA':more,'COEFFICIENTS':coefftable,'BINDATA':bindata,'SELDATA':seldata}
    for key,value in blocks.items():content=content.replace('@@'+key+'@@',value)
    assert '@@' not in content
    return content
def main():
    p=argparse.ArgumentParser();p.add_argument('--results',default='results/results.json');p.add_argument('--output',default='report/project_report.tex');a=p.parse_args()
    source=Path(a.results);source=source if source.is_absolute() else ROOT/source
    target=Path(a.output);target=target if target.is_absolute() else ROOT/target
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(generate(json.loads(source.read_text(encoding='utf-8'))),encoding='utf-8',newline='\n')
    print(f'Self-contained LaTeX report written: {target}')
if __name__=='__main__':main()
