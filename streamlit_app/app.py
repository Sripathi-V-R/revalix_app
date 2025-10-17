import re
import pandas as pd
import streamlit as st
import requests

# ===================== CONFIG =====================
st.set_page_config(page_title="🏠 ReValix Property Intelligence", layout="wide")

API_BASE_URL = st.secrets["revalix_api"]["url"]
ATTOM_API_KEY = st.secrets["attom"]["api_key"]

# ===================== HELPERS =====================
def normalize_address(addr: str) -> str:
    addr = addr.strip().upper()
    addr = re.sub(r"\s+", " ", addr)
    addr = addr.replace(",", "").replace(".", "")
    return addr

def get_apn_from_attom(address: str):
    url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/address"
    headers = {"apikey": ATTOM_API_KEY}
    params = {"address": address}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if "property" in data and len(data["property"]) > 0:
                return data["property"][0].get("identifier", {}).get("apn", None)
    except Exception as e:
        st.error(f"ATTOM API Error: {e}")
    return None

def fetch_property_from_api(acct_value: str):
    url = f"{API_BASE_URL}/property/{acct_value}"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code == 200:
            return res.json()
        else:
            st.error(f"API Error {res.status_code}: {res.text}")
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")
    return {}

# ===================== FIELD MAPPING =====================
mapping_by_table = {
    "Real_acct_owner_real_acct": {
        "acct": "Property ID",
        "yr": "Current Tax Year",
        "mailto": "Owner Name(s)",
        "mail_addr_1": "Mailing Address Line 1",
        "mail_city": "Mailing City",
        "mail_state": "Mailing State",
        "mail_zip": "Mailing ZIP Code",
        "site_addr_1": "Address Line 1",
        "site_addr_2": "City",
        "site_addr_3": "Postal Code",
        "Neighborhood_Grp": "Neighborhood Name",
        "Market_Area_1_Dscr": "Market",
        "Market_Area_2_Dscr": "Tax District",
        "yr_impr": "Year of Construction",
        "acreage": "Land Area(Acre)",
        "land_val": "Land Assessed Value",
        "bld_val": "Improvements Assessed Value",
        "assessed_val": "Assessed Value",
        "tot_appr_val": "Current Appraised Value",
        "tot_mkt_val": "Current Market Value",
        "lgl_1": "Legal Description",
        "lgl_2": "Legal Description",
        "jurs": "Legal Jurisdictions",
    },
    "Real_acct_owner_Deeds": {
        "dos": "Registration Date",
        "clerk_id": "Registration No.",
        "deed_id": "Type of Deed / Instrument",
    },
    "Real_acct_owner_Owners": {
        "name": "Owner Name(s)",
        "aka": "Grantor (Seller)",
        "pct_own": "Ownership Percentage",
    },
    "Real_acct_owner_permits": {
        "id": "Building Permit ID",
        "status": "Permit Status",
        "dscr": "Permit Description",
        "permit_tp_descr": "Permit Type Description",
        "property_tp": "Property Type",
        "issue_date": "Permit Issue Date",
        "yr": "Permit Year",
    },
    "Real_acct_ownership_historyownership_history": {
        "purchase_date": "Purchase Date / Sale Date",
        "site_address": "Property Address",
    },
}

def map_table_fields(df, table_name):
    if df.empty:
        return pd.DataFrame(columns=["Field", "Value"])
    mapping = mapping_by_table.get(table_name, {})
    row = df.iloc[0].to_dict()
    mapped = {}
    for col, val in row.items():
        if col in mapping:
            field_name = mapping[col]
            if field_name == "Legal Description" and field_name in mapped:
                mapped[field_name] += f" {val}" if val else ""
            else:
                mapped[field_name] = val
    return pd.DataFrame(list(mapped.items()), columns=["Field", "Value"])

section_groups = {
    "🏠 Property Overview": [
        "Property ID", "Address Line 1", "City", "Postal Code", "Market",
        "Neighborhood Name", "Year of Construction", "Land Area(Acre)"
    ],
    "👤 Owner Information": [
        "Owner Name(s)", "Grantor (Seller)", "Ownership Percentage",
        "Mailing Address Line 1", "Mailing City", "Mailing State", "Mailing ZIP Code"
    ],
    "💰 Valuation & Tax": [
        "Current Market Value", "Current Appraised Value", "Assessed Value",
        "Land Assessed Value", "Improvements Assessed Value", "Current Tax Year", "Tax District"
    ],
    "🏗️ Permit Details": [
        "Building Permit ID", "Permit Description", "Permit Year",
        "Permit Issue Date", "Permit Type Description", "Permit Status"
    ],
    "📜 Deed & Legal": [
        "Type of Deed / Instrument", "Registration No.", "Registration Date",
        "Legal Description", "Legal Jurisdictions"
    ],
    "🕰️ History": ["Purchase Date / Sale Date"],
}

# ===================== STYLING =====================
st.markdown("""
<style>
.section-card {
    background-color: #f9fafb;
    padding: 18px 25px;
    border-radius: 12px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.05);
    margin-bottom: 25px;
}
.section-header { color: #1E3A8A; font-size: 20px; font-weight: 600; margin-bottom: 10px; }
.field-label { color: #374151; font-weight: 500; }
.field-value { color: #111827; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ===================== MAIN UI =====================
st.title("🏠 ReValix Property Intelligence")
st.caption("AI-Powered Property Data Lookup via Secure API")

address_input = st.text_input("📍 Enter Property Address", placeholder="e.g. 4702 Spencer Hwy, Pasadena, TX 77505")

if address_input:
    normalized = normalize_address(address_input)
    st.info(f"**Normalized Property Address:** {normalized}")

    with st.spinner("🔍 Retrieving property data..."):
        apn = get_apn_from_attom(normalized)
        if not apn:
            st.error("❌ Unable to find APN for this address.")
            st.stop()

        data = fetch_property_from_api(apn)
        if not data:
            st.error("No property data found in API.")
            st.stop()

        combined_df = pd.DataFrame(columns=["Field", "Value"])
        for t, records in data.items():
            if not records:
                continue
            df = pd.DataFrame(records)
            mapped = map_table_fields(df, t)
            combined_df = pd.concat([combined_df, mapped], ignore_index=True)

    if combined_df.empty:
        st.error("No property data found in database.")
        st.stop()

    summary = {
        "Property Address": normalized,
        "Owner": combined_df.loc[combined_df["Field"] == "Owner Name(s)", "Value"].values[0] if "Owner Name(s)" in combined_df["Field"].values else "N/A",
        "Market Value": combined_df.loc[combined_df["Field"] == "Current Market Value", "Value"].values[0] if "Current Market Value" in combined_df["Field"].values else "N/A",
        "Year Built": combined_df.loc[combined_df["Field"] == "Year of Construction", "Value"].values[0] if "Year of Construction" in combined_df["Field"].values else "N/A",
        "Land Area": combined_df.loc[combined_df["Field"] == "Land Area(Acre)", "Value"].values[0] if "Land Area(Acre)" in combined_df["Field"].values else "N/A",
    }

    st.markdown(f"""
    <div class="section-card" style="background-color:#EFF6FF;">
        <div class="section-header">🏡 Property Summary</div>
        <p><b>Property Address:</b> {summary['Property Address']}<br>
        <b>Owner:</b> {summary['Owner']}<br>
        <b>Market Value:</b> ${summary['Market Value']}<br>
        <b>Year Built:</b> {summary['Year Built']}<br>
        <b>Land Area:</b> {summary['Land Area']} acres</p>
    </div>
    """, unsafe_allow_html=True)

    for section, fields in section_groups.items():
        section_data = combined_df[combined_df["Field"].isin(fields)]
        if not section_data.empty:
            st.markdown(f"<div class='section-card'><div class='section-header'>{section}</div>", unsafe_allow_html=True)
            for _, row in section_data.iterrows():
                st.markdown(f"<p class='field-label'>{row['Field']}: <span class='field-value'>{row['Value']}</span></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    safe_filename = normalized.replace(" ", "_")
    csv = combined_df.to_csv(index=False).encode('utf-8')
    json_data = combined_df.to_json(orient="records", indent=2)
    st.download_button("⬇️ Download CSV", data=csv, file_name=f"{safe_filename}.csv", mime="text/csv")
    st.download_button("⬇️ Download JSON", data=json_data, file_name=f"{safe_filename}.json", mime="application/json")
