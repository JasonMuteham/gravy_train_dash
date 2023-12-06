import streamlit as st
import pydeck as pdk
import geopandas as gpd
import pandas as pd
import json
#from duckdb_connection import DuckDBConnection
import gravysql
import duckdb

st.set_page_config(
    page_title="The Gravy Train",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

#db= f"md:gravy_train?motherduck_token={st.secrets['MOTHERDUCK_TOKEN']}"

#conn = st.connection("duckdb", type=DuckDBConnection, database=db)

conn = duckdb.connect()

with open('data/colorbrewer.json') as f:
  colour_brewer = json.load(f)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

bins = 9


selected_year = 2022

def get_financial_year(yr):
    fin_yr = int(yr[2:])
    return f"{fin_yr}_{fin_yr+1}"

st.sidebar.header("GravyTrain `V1.0.0`")
selected_year = st.sidebar.number_input('Choose a year to view', min_value=2010, max_value=2025, value=selected_year, step=1, help="The financial year runs from 1 April to 31 March")

financial_year = get_financial_year(str(selected_year))
st.subheader(f'MP Expense Analysis for financial year 20{financial_year[0:2]}-20{financial_year[3:]}')
map_colour = st.sidebar.selectbox(
    'Colour scheme',('Viridis','OrRd','PuBu','BuPu','Oranges','BuGn','YlOrBr','YlGn','Reds','RdOu','Greens','YlGnBu','Purples','GnBu','Greys','YlOrRd','PuRd','Blues','PuBuGn'),index=0, help = "Colour scheme for map")

colour_scheme = colour_brewer[f"{map_colour}"][f"{bins}"]


colour = st.sidebar.radio(
    'Colour value',
    options=['Total Cost','Cost per mile'],horizontal=True)

incumbent = st.sidebar.toggle('Incumbent MP',value=False, help = "On election or by-election year which MP to use.")

cost_category = st.sidebar.multiselect('Select cost categories',['Accommodation','MP Travel','Miscellaneous','Staffing','Winding Up',
                        'Office Costs','Office Costs Expenditure','Staff Travel','Travel','Dependant Travel','Miscellaneous expenses','Start Up'],['Accommodation','MP Travel'])
if cost_category == []:
    st.sidebar.error("Please select at least one cost category")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Map", "About", "Analysis"])

with tab1:
    INITIAL_VIEW_STATE = pdk.ViewState( latitude=54.5, longitude=-2, 
                                    zoom=4.5, max_zoom=10, min_zoom=4,
                                    pitch=28, bearing=0,
                                    height=600)

    

    def getfillcolour(bin):
        return colour_scheme[(bins-1) - bin]
                      
    with st.spinner('Getting the data...'):

        uk_geo = gpd.read_file('data/constituency_geometry.geojson')
        mps = gravysql.get_mps(conn, financial_year, incumbent)
        mp_geo = uk_geo.merge(mps, left_on=['constituency_id'], right_on=['constituency_code'], how='left')
        data = gravysql.get_expenses(conn, financial_year, cost_category)
        if data.empty:
            st.warning(f'No data found for financial year {financial_year} and cost category {cost_category}')
            st.stop()

        uk = mp_geo.merge(data, left_on=['id'], right_on=['mp_id'], how='left')
        
        uk = uk.rename(columns={"constituency_x": "constituency", 
                        "party_colour_code_x": "party_colour_code",
                        "full_name_x": "full_name",
                        "party_name_x": "party_name"})
        
        uk["total_amount"] = uk["total_amount"].fillna(0)
        uk["mph"] = uk["total_amount"]/uk["miles_to_HP"]
        uk["mph"] = uk["mph"].round(2)
        uk["elevation"] = uk["total_amount"]

        if colour == 'Total Cost':
            uk["bin"] = pd.cut(uk["total_amount"], bins, labels=False)
        else:
            uk["bin"] = pd.cut(uk["mph"], bins, labels=False)

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
            "html": "{constituency_name}<br />{full_name} ({party_name})<br />Total: £{total_amount}<br />HP: {miles_to_HP} miles<br />£{mph} per mile",
            "style": {
            "font-family": "Source Sans Pro, sans-serif",
            "color": "white"}
        }

        r = pdk.Deck(
            map_provider=None,
            layers=[ geojson], 
            initial_view_state=INITIAL_VIEW_STATE, 
            tooltip=tooltip
        )

        st.pydeck_chart(r, use_container_width=True)

        html_file = r.to_html(filename=None, as_string=True)

        st.sidebar.download_button(
            label="Download map",
            data=html_file,
            file_name='map.html',
            mime='text/html',
            type='primary'
        )