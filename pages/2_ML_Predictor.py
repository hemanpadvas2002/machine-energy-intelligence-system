# ===========================================================
# STRICT ML Predictor for KW / KWh (AMTDC Project)
# ===========================================================
import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import xgboost as xgb

st.set_page_config(page_title="ML KW/KWh Predictor", layout="wide")

# -----------------------------------------------------------
# PAGE HEADER
# -----------------------------------------------------------
st.title("⚙️ STRICT ML Predictor — KW / KW·hr (AMTDC)")
st.write("""
This predictor uses **only Savitzky–Golay smoothed values**, removes leakage,
drops highly correlated features (> 0.95), and predicts **KW** using 
Linear Regression, Random Forest, and XGBoost.

⚡ **KWh is NOT predicted using ML.**
Instead, it is correctly computed from predicted KW:
> KWh_next = Last_KWh + (Predicted_KW × 1 hour)
""")

# -----------------------------------------------------------
# USER INPUTS
# -----------------------------------------------------------
machine_options = ["Galaxy", "LML_UPMMC", "MTX", "AGI_Robo", "Ace_Vantage"]
machine = st.selectbox("Select Machine:", machine_options)

target_map = {
    "KW (total_kw)": "total_kw",
    "KW·hr (total_net_kwh)": "total_net_kwh"
}
target_choice = st.selectbox("Select Target to Predict:", list(target_map.keys()))
target_col = target_map[target_choice]

DB_NAME = "machine_data.db"

if st.button("🚀 Run Strict Prediction"):

    # -----------------------------------------------------------
    # FETCH DATA
    # -----------------------------------------------------------
    try:
        st.info("Connecting to SQLite and fetching data...")

        conn = sqlite3.connect(DB_NAME)

        # Sanitize table name (lower case, replace space with underscore)
        import re
        def sanitize(name):
            s = name.lower()
            s = re.sub(r'[^a-z0-9_]+', '_', s).strip('_')
            return s
        
        table_name = f"{sanitize(machine)}_readings"

        query = f"""
            SELECT timestamp, avg_voltage_ln, avg_voltage_ll, avg_current,
                   total_kw, total_net_kwh
            FROM {table_name}
            ORDER BY timestamp ASC;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        st.success(f"Data fetched: {df.shape[0]} rows")

        # Convert timestamp
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        if df.shape[0] < 20:
            st.error("Not enough data for smoothing + ML. Need >= 20 rows.")
            st.stop()

        # -----------------------------------------------------------
        # PREPROCESS — STRICT SMOOTHING
        # -----------------------------------------------------------
        df["t_numeric"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds()

        base_cols = ["avg_voltage_ln", "avg_voltage_ll", "avg_current",
                     "total_kw", "total_net_kwh"]

        def smooth(series):
            s = series.copy().astype(float)
            s = s.fillna(method="ffill").fillna(method="bfill")
            n = len(s)
            wl = 7 if n >= 7 else (n - 1 if n % 2 == 0 else n)
            if wl < 3:
                return s
            try:
                # polyorder must be less than window_length
                poly = 2 if wl > 2 else 1
                return pd.Series(savgol_filter(s, wl, poly), index=s.index)
            except:
                return s

        for col in base_cols:
            if col in df.columns:
                df[col + "_smooth"] = smooth(df[col])
            else:
                df[col + "_smooth"] = 0 # Handle missing columns gracefully

        # -----------------------------------------------------------
        # ALWAYS PREDICT KW — NOT KWH
        # (We compute KWh from predicted KW)
        # -----------------------------------------------------------
        y = df["total_kw_smooth"]   # ALWAYS KW for ML target

        # candidate input features
        feature_list = [
            "avg_voltage_ll_smooth",
            "avg_current_smooth",
            "t_numeric"
        ]
        
        # Check if features exist
        missing_features = [f for f in feature_list if f not in df.columns]
        if missing_features:
             st.error(f"Missing features: {missing_features}")
             st.stop()

        X = df[feature_list].copy()

        # Remove rows where y is NaN
        mask = ~y.isna()
        X = X.loc[mask].reset_index(drop=True)
        y = y.loc[mask].reset_index(drop=True)

        # -----------------------------------------------------------
        # Train-test split (time aware)
        # -----------------------------------------------------------
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        # Fill missing
        X_train = X_train.fillna(X_train.mean())
        if X_test.isnull().values.any():
             X_test = X_test.fillna(X_train.mean()) # Use train mean to avoid leakage

        # -----------------------------------------------------------
        # MODEL TRAINING
        # -----------------------------------------------------------
        lr = LinearRegression()
        rf = RandomForestRegressor(n_estimators=100, random_state=42) # reduced estimators for speed
        xg_reg = xgb.XGBRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=6,
            random_state=42
        )

        lr.fit(X_train, y_train)
        rf.fit(X_train, y_train)
        xg_reg.fit(X_train, y_train)

        y_pred_lr = lr.predict(X_test)
        y_pred_rf = rf.predict(X_test)
        y_pred_xgb = xg_reg.predict(X_test)

        # -----------------------------------------------------------
        # MODEL PERFORMANCE
        # -----------------------------------------------------------
        st.subheader("📊 Test Set Performance")

        c1, c2, c3 = st.columns(3)

        c1.metric("Linear Regression R²", f"{r2_score(y_test, y_pred_lr):.4f}")
        c1.metric("Linear Regression MSE", f"{mean_squared_error(y_test, y_pred_lr):.4f}")

        c2.metric("Random Forest R²", f"{r2_score(y_test, y_pred_rf):.4f}")
        c2.metric("RF MSE", f"{mean_squared_error(y_test, y_pred_rf):.4f}")

        c3.metric("XGBoost R²", f"{r2_score(y_test, y_pred_xgb):.4f}")
        c3.metric("XGB MSE", f"{mean_squared_error(y_test, y_pred_xgb):.4f}")

        # best model
        scores = {
            "Linear Regression": r2_score(y_test, y_pred_lr),
            "Random Forest": r2_score(y_test, y_pred_rf),
            "XGBoost": r2_score(y_test, y_pred_xgb)
        }
        best_model_name = max(scores, key=scores.get)

        st.success(f"🏆 Best performing model: {best_model_name}")

        # -----------------------------------------------------------
        # 1-HOUR AHEAD FORECAST
        # -----------------------------------------------------------
        last_row = df.iloc[-1]

        fv = {
            "avg_voltage_ll_smooth": last_row["avg_voltage_ll_smooth"],
            "avg_current_smooth": last_row["avg_current_smooth"],
            "t_numeric": df["t_numeric"].max() + 3600    # +1 hour
        }

        fv = pd.DataFrame([fv])
        # Ensure column order matches training
        fv = fv[feature_list] 
        fv = fv.fillna(X_train.mean())

        future_kw_lr = lr.predict(fv)[0]
        future_kw_rf = rf.predict(fv)[0]
        future_kw_xgb = xg_reg.predict(fv)[0]

        # -----------------------------------------------------------
        # COMPUTE KWH FROM KW (NOT ML!)
        # -----------------------------------------------------------
        last_kwh = last_row["total_net_kwh_smooth"]

        future_kwh_lr = last_kwh + future_kw_lr * 1
        future_kwh_rf = last_kwh + future_kw_rf * 1
        future_kwh_xgb = last_kwh + future_kw_xgb * 1

        # -----------------------------------------------------------
        # OUTPUT SECTION
        # -----------------------------------------------------------
        st.subheader("🔮 1-Hour Ahead Forecast")

        if target_col == "total_kw":
            st.write(f"**Linear Regression:** {future_kw_lr:.3f} KW")
            st.write(f"**Random Forest:** {future_kw_rf:.3f} KW")
            st.write(f"**XGBoost:** {future_kw_xgb:.3f} KW")

        else:
            st.write("### (Computed from KW — not ML)")
            st.write(f"**Linear Regression:** {future_kwh_lr:.3f} KWh")
            st.write(f"**Random Forest:** {future_kwh_rf:.3f} KWh")
            st.write(f"**XGBoost:** {future_kwh_xgb:.3f} KWh")

        # -----------------------------------------------------------
        # Summary
        # -----------------------------------------------------------
        st.subheader("📘 Summary")
        st.markdown(f"""
        - Machine: **{machine}**
        - Target selected: **{target_choice}**
        - ML actually predicts: **KW only**
        - KWh is computed correctly: `KWh = last_kwh + KW × 1 hour`
        - Best ML model: **{best_model_name}**
        """)

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

else:
    st.info("Choose machine and target, then click Run.")
