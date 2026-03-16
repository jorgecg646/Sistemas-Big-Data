"""
IPC vs IPV Regression Analysis — Predictive modeling (IPC -> IPV).
Models: Linear, Ridge, Lasso, Polynomial(deg=2).
Pipeline: Scaling -> Train/Test -> GridSearchCV -> Cross-validation -> Overfitting check.
"""

import os, numpy as np, polars as pl, pandas as pd
import plotly.express as px, plotly.graph_objects as go
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.pipeline import Pipeline

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data_output")
VIS_DIR  = os.path.join(os.path.dirname(__file__), "..", "visualizations")
os.makedirs(VIS_DIR, exist_ok=True)

TPL = "plotly_dark"
HOUSING_COLORS = {"General": "#4ECDC4", "Vivienda nueva": "#FFD93D", "Vivienda segunda mano": "#6C5CE7"}
ALPHAS = [0.001, 0.01, 0.1, 1, 10, 100]
SEED = 42


# ── Data helpers ──────────────────────────────────────────────────────

def load_csv(name, col="Fecha_Fecha"):
    """Load CSV (semicolon sep, decimal comma) and add Quarter column."""
    df = pl.read_csv(os.path.join(DATA_DIR, name), separator=";",
                     decimal_comma=True, infer_schema_length=500)
    quarter = lambda d: (int(d.split("-")[1]) - 1) // 3 + 1
    return df.with_columns(pl.col(col).cast(pl.String)
              .map_elements(quarter, return_dtype=pl.Int64).alias("Quarter"))


def merge(df_ipc, df_ipv, ccaa=None, htype=None):
    """Cross IPC (quarterly mean) with IPV (annual var) by year+quarter."""
    ipc = df_ipc.group_by(["Anyo","Quarter"]).agg(
        pl.col("IPC_Variacion_Anual").mean().alias("IPC")).drop_nulls()
    ipv = df_ipv.filter(pl.col("Metrica") == "Variación anual")
    if ccaa:  ipv = ipv.filter(pl.col("CCAA") == ccaa)
    if htype: ipv = ipv.filter(pl.col("Tipo_Vivienda") == htype)
    ipv = ipv.group_by(["Anyo","Quarter"]).agg(
        pl.col("Valor").mean().alias("IPV")).drop_nulls()
    return ipc.join(ipv, on=["Anyo","Quarter"], how="inner").sort(["Anyo","Quarter"]).drop_nulls()


# ── Model comparison engine ──────────────────────────────────────────

def compare_models(X, y, verbose=True):
    """Train Linear/Ridge/Lasso/Poly, tune with GridSearchCV, evaluate with
    train/test split + cross-validation. Returns best model info dict.

    StandardScaler applied because Ridge/Lasso penalties are scale-dependent;
    without it, features with larger magnitudes dominate the regularisation.
    """
    # Too few samples for split → fallback to simple fit
    if len(X) < 6:
        m = LinearRegression().fit(X, y)
        yp = m.predict(X)
        s = r2_score(y, yp)
        return dict(name="LinearRegression", model=m, scaler=None, y_pred=yp,
                    r2_tr=s, r2_te=s, rmse=np.sqrt(mean_squared_error(y,yp)),
                    mae=mean_absolute_error(y,yp), cv=np.nan, cv_std=np.nan, all=[])

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    Xtr, Xte, ytr, yte = train_test_split(Xs, y, test_size=0.2, random_state=SEED)
    n_cv = min(5, len(Xtr))

    candidates = {
        "LinearRegression": LinearRegression(),
        "Ridge (GridSearchCV)": GridSearchCV(Ridge(), {"alpha": ALPHAS}, cv=n_cv, scoring="r2"),
        "Lasso (GridSearchCV)": GridSearchCV(Lasso(max_iter=10000), {"alpha": ALPHAS}, cv=n_cv, scoring="r2"),
    }
    if len(Xtr) >= 8:
        candidates["Polynomial (deg=2)"] = Pipeline([
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("lr", LinearRegression())])

    results = []
    for name, mdl in candidates.items():
        mdl.fit(Xtr, ytr)
        est = mdl.best_estimator_ if isinstance(mdl, GridSearchCV) else mdl
        alpha = mdl.best_params_.get("alpha") if isinstance(mdl, GridSearchCV) else None
        cv = cross_val_score(est, Xs, y, cv=min(5, len(Xs)), scoring="r2")
        results.append(dict(
            name=name, model=est, alpha=alpha,
            r2_tr=r2_score(ytr, est.predict(Xtr)),
            r2_te=r2_score(yte, est.predict(Xte)),
            rmse=np.sqrt(mean_squared_error(yte, est.predict(Xte))),
            mae=mean_absolute_error(yte, est.predict(Xte)),
            cv=cv.mean(), cv_std=cv.std()))

    best = max(results, key=lambda r: r["cv"])

    if verbose:
        print(f"\n  {'Model':<25} {'R2_tr':>7} {'R2_te':>7} {'RMSE':>8} {'CV_R2':>10} {'Alpha':>7}")
        print("  " + "-" * 70)
        for r in results:
            a = f"{r['alpha']:.3f}" if r["alpha"] else "  N/A"
            tag = " *" if r["name"] == best["name"] else ""
            print(f"  {r['name']:<25} {r['r2_tr']:>7.4f} {r['r2_te']:>7.4f} "
                  f"{r['rmse']:>8.4f} {r['cv']:>.4f}±{r['cv_std']:.3f} {a}{tag}")
        gap = best["r2_tr"] - best["r2_te"]
        sym = "⚠ Overfitting" if gap > 0.2 else "✓ No overfitting"
        print(f"  {sym} (gap={gap:.3f})")

    best["y_pred"] = best["model"].predict(scaler.transform(X))
    best["scaler"] = scaler
    best["all"] = results
    return best


# ── Shared plotting helpers ──────────────────────────────────────────

def save_html(fig, name):
    """Write figure to VIS_DIR and print confirmation."""
    fig.write_html(os.path.join(VIS_DIR, name))
    print(f"  -> {name}")


def regression_line(model, scaler, X, margin=1):
    """Generate smooth x/y arrays for the regression line."""
    xr = np.linspace(X.min()-margin, X.max()+margin, 100).reshape(-1,1)
    yr = model.predict(scaler.transform(xr) if scaler else xr)
    return xr.flatten(), yr.flatten()


def metrics_text(res):
    """Format a compact annotation string from a result dict."""
    parts = [f"<b>{res['name']}</b>",
             f"R² tr={res['r2_tr']:.4f} | te={res['r2_te']:.4f}",
             f"RMSE={res['rmse']:.3f} | MAE={res['mae']:.3f}"]
    if not np.isnan(res.get("cv", np.nan)):
        parts.append(f"CV R²={res['cv']:.4f}±{res['cv_std']:.3f}")
    return "<br>".join(parts)


def add_annotation(fig, text):
    fig.add_annotation(x=.02, y=.98, xref="paper", yref="paper", text=text,
        showarrow=False, font=dict(size=12, color="white"),
        bgcolor="rgba(0,0,0,.6)", bordercolor="white", borderwidth=1, align="left")


# ── MODEL 1: National ────────────────────────────────────────────────

def model_national(df_ipc, df_ipv):
    print("\n" + "="*60 + "\n  MODEL 1: National (Spain)\n" + "="*60)
    data = merge(df_ipc, df_ipv, ccaa="Total Nacional", htype="General")
    if len(data) < 3: print("  Insufficient data"); return

    pdf = data.to_pandas()
    X, y = pdf[["IPC"]].values, pdf["IPV"].values
    res = compare_models(X, y)

    # Scatter + regression line
    xl, yl = regression_line(res["model"], res["scaler"], X)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pdf["IPC"], y=pdf["IPV"], mode="markers",
        marker=dict(size=12, color=pdf["Anyo"], colorscale="Viridis",
                    showscale=True, colorbar=dict(title="Year"),
                    line=dict(width=1, color="white")),
        text=[f"Y:{a} Q{q}" for a,q in zip(pdf["Anyo"],pdf["Quarter"])],
        hovertemplate="IPC:%{x:.1f}%<br>IPV:%{y:.1f}%<br>%{text}<extra></extra>", name="Data"))
    fig.add_trace(go.Scatter(x=xl, y=yl, mode="lines",
        line=dict(color="#FF6B6B", width=3, dash="dash"),
        name=f"{res['name']} (R²={res['r2_te']:.3f})"))
    add_annotation(fig, metrics_text(res))
    fig.update_layout(title="Model 1: IPC → IPV (National Spain)",
        xaxis_title="IPC Annual Var (%)", yaxis_title="IPV Annual Var (%)",
        template=TPL, height=650,
        legend=dict(x=.02, y=.02, xanchor="left", yanchor="bottom", bgcolor="rgba(0,0,0,.5)"))
    save_html(fig, "regresion_general_espana.html")


# ── MODEL 2: By CCAA ─────────────────────────────────────────────────

def model_by_ccaa(df_ipc, df_ipv):
    print("\n" + "="*60 + "\n  MODEL 2: By Autonomous Community\n" + "="*60)
    ccaas = (df_ipv.filter((pl.col("CCAA")!="Total Nacional") &
             (pl.col("Metrica")=="Variación anual") & (pl.col("Tipo_Vivienda")=="General"))
             .select("CCAA").unique().sort("CCAA").to_series().to_list())
    if not ccaas: print("  No CCAA found"); return

    rows, dfs = [], []
    for ccaa in ccaas:
        data = merge(df_ipc, df_ipv, ccaa=ccaa, htype="General")
        if len(data) < 3: continue
        pdf = data.to_pandas()
        res = compare_models(pdf[["IPC"]].values, pdf["IPV"].values, verbose=False)
        rows.append(dict(CCAA=ccaa, Model=res["name"], R2=round(res["r2_te"],4),
                         RMSE=round(res["rmse"],4), N=len(pdf)))
        pdf["CCAA"], pdf["y_pred"] = ccaa, res["y_pred"]
        dfs.append(pdf)

    if not rows: print("  No results"); return
    df_r = pl.DataFrame(rows).sort("R2", descending=True)
    for r in df_r.iter_rows(named=True):
        print(f"  {r['CCAA']:<35} {r['Model']:<20} R²={r['R2']:.4f}  N={r['N']}")

    # Faceted scatter (top 9)
    all_df = pd.concat(dfs, ignore_index=True)
    top9 = df_r.head(9).select("CCAA").to_series().to_list()
    fig = px.scatter(all_df[all_df["CCAA"].isin(top9)], x="IPC", y="IPV",
        facet_col="CCAA", facet_col_wrap=3, trendline="ols", color="Anyo",
        color_continuous_scale="Viridis", labels={"IPC":"IPC (%)","IPV":"IPV (%)","Anyo":"Year"},
        title="Model 2: IPC → IPV by CCAA (Top 9 R²)", template=TPL, height=900)
    fig.update_traces(marker=dict(size=8, line=dict(width=.5, color="white")))
    save_html(fig, "regresion_por_ccaa.html")

    # R² ranking bar chart
    fig2 = px.bar(df_r.to_pandas(), x="R2", y="CCAA", orientation="h",
        color="R2", color_continuous_scale="RdYlGn",
        labels={"R2":"R² (Test)","CCAA":"Autonomous Community"},
        title="Model 2: R² Ranking by CCAA", template=TPL, height=600)
    fig2.update_layout(yaxis=dict(categoryorder="total ascending"))
    save_html(fig2, "regresion_r2_por_ccaa.html")


# ── MODEL 3: By housing type ─────────────────────────────────────────

def model_by_housing_type(df_ipc, df_ipv):
    print("\n" + "="*60 + "\n  MODEL 3: By Housing Type (National)\n" + "="*60)
    fig, summaries = go.Figure(), []

    for htype in ["General", "Vivienda nueva", "Vivienda segunda mano"]:
        data = merge(df_ipc, df_ipv, ccaa="Total Nacional", htype=htype)
        if len(data) < 3: continue
        pdf = data.to_pandas()
        X, y = pdf[["IPC"]].values, pdf["IPV"].values
        res = compare_models(X, y)
        color = HOUSING_COLORS.get(htype, "#FFF")
        summaries.append(f"<b>{htype}</b>: {res['name']} R²={res['r2_te']:.3f}")

        fig.add_trace(go.Scatter(x=pdf["IPC"], y=pdf["IPV"], mode="markers",
            marker=dict(size=10, color=color, line=dict(width=1, color="white")),
            name=htype, hovertemplate=f"{htype}<br>IPC:%{{x:.1f}}%<br>IPV:%{{y:.1f}}%<extra></extra>"))
        xl, yl = regression_line(res["model"], res["scaler"], X)
        fig.add_trace(go.Scatter(x=xl, y=yl, mode="lines",
            line=dict(color=color, width=2.5, dash="dash"), name=f"{htype} (R²={res['r2_te']:.3f})"))

    if not summaries: print("  No results"); return
    add_annotation(fig, "<br>".join(summaries))
    fig.update_layout(title="Model 3: IPC → IPV by Housing Type (Spain)",
        xaxis_title="IPC Annual Var (%)", yaxis_title="IPV Annual Var (%)",
        template=TPL, height=650,
        legend=dict(x=.02, y=.02, xanchor="left", yanchor="bottom", bgcolor="rgba(0,0,0,.5)"))
    save_html(fig, "regresion_tipo_vivienda.html")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("Loading datasets...")
    df_ipc, df_ipv = load_csv("ipc_clean.csv"), load_csv("ipv_clean.csv")
    print(f"  IPC: {len(df_ipc)} rows | IPV: {len(df_ipv)} rows")
    model_national(df_ipc, df_ipv)
    model_by_ccaa(df_ipc, df_ipv)
    model_by_housing_type(df_ipc, df_ipv)
    print("\n  Done. Charts in visualizations/")

if __name__ == "__main__":
    main()
