import streamlit as st
import pydeck as pdk
import geopandas as gpd
import pandas as pd
import json
import gravysql

st.set_page_config(
    page_title="The Gravy Train",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://jasonmuteham.github.io/Portfolio/',
        'Report a bug': "mailto:ancientwrangler@gmail.com",
        'About': 'The Gravy Train, a geospatial visualization of UK Member of Parliament expenses by [Jason Muteham](https://jasonmuteham.github.io/Portfolio/)'
          
    }
)


with open('data/colorbrewer.json') as f:
  colour_brewer = json.load(f)

with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

bins = 9
selected_year = 2020


def get_financial_year(yr):
    fin_yr = int(yr[2:])
    return f"{fin_yr}_{fin_yr+1}"

st.sidebar.header("GravyTrain `V1.0.3`")
st.sidebar.write("Data Updated `2023-12-02`")
selected_year = st.sidebar.number_input('Choose a year to view', min_value=2010, max_value=2023, value=selected_year, step=1, help="The financial year runs from 1 April to 31 March")

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

def getfillcolour(bin):
    return colour_scheme[(bins-1) - bin]

tab1, tab2 = st.tabs(["Map", "About"])

with tab1:

    INITIAL_VIEW_STATE = pdk.ViewState( latitude=51.2, longitude=0, 
                                    zoom=8, max_zoom=10, min_zoom=4,
                                    pitch=28, bearing=0,
                                    height=600)
                  
    with st.spinner('Getting the data...'):

        uk_geo = gpd.read_file('data/constituency_geometry.geojson')
        mps = gravysql.get_mps(financial_year, incumbent)
        mp_geo = uk_geo.merge(mps, left_on=['constituency_id'], right_on=['constituency_code'], how='left')
        data = gravysql.get_expenses(financial_year, cost_category)
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
            "html": "{constituency_name}<br />{full_name} ({party_name})<br />Total: £{total_amount}<br />Houses of Parliament: {miles_to_HP} miles<br />£{mph} per mile",
            "style": {
            "font-family": "Source Sans Pro, sans-serif",
            "color": "white"}
        }

        r = pdk.Deck(
            map_provider=None,
            layers=[geojson], 
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
            type='primary',
            help = 'Download the map as an HTML file'
         )

with tab2:

    """
### Geospatial Visualization of UK Member of Parliament Expenses

MP expenses are a hot topic in the UK, and my MP raised eyebrows with large claims for rented accommodation, even though they live in a constituency close to Parliament. This made me wonder if the outrage was justified.

- Would combining travel and accommodation expenses provide a fair picture?

- How do MPs in distant constituencies compare? 

- Is travelling from Scotland and staying in hotels comparable to permanently renting a home in London?

- Should we assess costs per mile instead of total expenses?

The outcome? The Gravy Train. Now armed with data, the question is: How does your MP's spending compare?

Data is supplied by 

- UK Parliament [https://www.parliament.uk/]

- Independent Parliamentary Standards Authority [https://www.theipsa.org.uk/]

Over 2 million expense records form the basis of the analysis and the underlying database.

The IPSA release updates every two months, however data available for the two most recent financial years might not yet reflect the final positions for those years.

The financial period is 1st April - 31st March.

The distance to the Houses of Parliament is calculated as the distance from the Houses of parliament to the centre of a constituency.

For more information about the pipeline and data stack [https://jasonmuteham.github.io/Portfolio/gravytrain.html]

    """