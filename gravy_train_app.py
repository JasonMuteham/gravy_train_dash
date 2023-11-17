import streamlit as st
import pydeck as pdk
import geopandas as gpd
import pandas as pd
import json

st.set_page_config(
    page_title="The Gravy Train",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

with open('data\colorbrewer.json') as f:
  colour_brewer = json.load(f)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

api_url = st.secrets["api_url"]
DATA_URL = "data\PCON_DEC_2021_UK_BUC.geojson"
bins = 9
colour_scheme = colour_brewer["MyViridis"][f"{bins}"]
cost_category = 'ALL' 
selected_year = '2022'

def get_financial_year(yr):
    fin_yr = int(yr[2:])
    return f"{fin_yr}_{fin_yr+1}"



st.sidebar.header("GravyTrain `V1.0.0`")
selected_year = st.sidebar.number_input('Choose a year to view', min_value=2010, max_value=2023, value=2022, step=1, help="The financial year runs from 1 April to 31 March")

financial_year = get_financial_year(str(selected_year))
st.subheader(f'MP Expense Analysis for financial year 20{financial_year[0:2]}-20{financial_year[3:]}')

#election_filter = st.sidebar.radio("Election Filter",["Old","New"], captions = ["Outgoing MP","Incoming MP"], help = "On election or by-election year which MP to use.")

election_filter = st.sidebar.selectbox("Election Filter",("Outgoing MP","Incoming MP"), help = "On election or by-election year which MP to use.")

tab1, tab2, tab3 = st.tabs(["Map", "About", "Analysis"])

with tab1:
    INITIAL_VIEW_STATE = pdk.ViewState( latitude=54.5, longitude=-2, 
                                    zoom=4.5, max_zoom=10, min_zoom=4,
                                    pitch=28, bearing=0,
                                    height=520)

    @st.cache_data
    def get_all_mps(fin_year):
        return pd.read_json(f'{api_url}/mps_basic/all?financial_year={fin_year}')

    @st.cache_data
    def get_data(category, fin_year):
        return pd.read_json(f'{api_url}/expenses/{fin_year}?cost_category={category}')

    def getfillcolour(bin):
        return colour_scheme[(bins-1) - bin]
                      
    with st.spinner('Getting the data...'):
        uk_geo = gpd.read_file(DATA_URL)
        mps = get_all_mps(financial_year)
        mp_geo = uk_geo.merge(mps, left_on=['PCON21CD'], right_on=['constituency_code'], how='left')
        data = get_data(cost_category, financial_year)
        uk = mp_geo.merge(data, left_on=['id'], right_on=['mp_id'], how='left')

        uk = uk.rename(columns={"constituency_x": "constituency", 
                        "party_colour_code_x": "party_colour_code",
                        "full_name_x": "full_name",
                        "party_name_x": "party_name"})
        
        uk["total_amount"] = uk["total_amount"].fillna(0)
        uk["elevation"] = uk["total_amount"]
        uk["bin"] = pd.cut(uk["elevation"], bins, labels=False)
        uk["cost_category"] = cost_category
        uk["fill_colour"] = uk["bin"].apply(getfillcolour)

    with st.spinner('Building the map...'):
        geojson = pdk.Layer(
            "GeoJsonLayer",
            uk,
            opacity=1,
            stroked=False,
            filled=True,
            extruded=True,
            wireframe=True,
            get_elevation="elevation",
            elevation_scale=.5,
            get_fill_color="fill_colour",
            get_line_color= [200, 200, 150],    
            pickable=True,
            auto_highlight=True
        )

        tooltip = {
            "html": "{constituency}<br />{full_name} ({party_name})<br />{cost_category}: £{total_amount}",
            "style": {
            "backgroundColor": "{party_colour}",
            "color": "white"}
        }

        r = pdk.Deck(
            map_provider=None,
            layers=[ geojson], 
            initial_view_state=INITIAL_VIEW_STATE, 
            tooltip=tooltip
        )

        st.pydeck_chart(r, use_container_width=True)
#r.to_html("geojson_layer.html")