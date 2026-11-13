import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(page_title='IS 445 HW6: Illinois State Buildings', layout='wide')

st.title('Illinois State Buildings: What Was Built, When, and By Whom')
st.text('IS 445 Homework 6 - Raymond Lu')
st.text('The URL for this app is: https://glorysing-is445-hw6.streamlit.app/')
st.text('The URL for its GitHub repo is: https://github.com/Glorysing/is445_hw6_streamlit')

st.write(
    "This report uses the Illinois **building inventory** dataset from the course data repository. "
    "Each row is one building owned by a state agency, with the year it was built, its size in "
    "square feet, what it is used for, and whether it is still in use."
)

data_url = 'https://raw.githubusercontent.com/UIUC-iSchool-DataViz/is445_data/main/building_inventory.csv'


@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    return df


df = load_data(data_url)

st.subheader('Data cleaning')
st.write(
    f"The raw file has {len(df):,} buildings. About 300 of them have a construction year or square "
    "footage of 0, which means the value is missing, so I removed them. I also removed the 46 buildings "
    "built before 1850, since there are only one or two per decade and they make the time axis very long. "
    "For the usage categories, I kept the 8 biggest categories (by total square footage) and grouped the "
    "small ones (Mercantile, Unusual, Utility, Public, Not provided) into 'Other'."
)

clean = df[(df['Year Constructed'] >= 1850) & (df['Square Footage'] > 0)].copy()
clean['Decade'] = (clean['Year Constructed'] // 10) * 10

clean['Usage'] = clean['Usage Description'].replace({'Detention & Correc': 'Detention & Correction'})
main_usages = ['Assembly', 'Business', 'Education', 'Storage', 'Industrial',
               'Detention & Correction', 'Health Care', 'Residential']
clean.loc[~clean['Usage'].isin(main_usages), 'Usage'] = 'Other'

st.write(f"After cleaning there are {len(clean):,} buildings left.")

with st.expander('Show the cleaned data'):
    st.dataframe(clean[['Agency Name', 'Location Name', 'City', 'Year Constructed',
                        'Square Footage', 'Total Floors', 'Usage', 'Bldg Status']])

# ---------------- Plot 1 ----------------
st.header('Plot 1: How much did the state build in each decade?')

measure = st.radio('Show bar height as:', ['Total square footage', 'Number of buildings'],
                   horizontal=True)

decade_usage = clean.groupby(['Decade', 'Usage']).agg(
    sqft=('Square Footage', 'sum'),
    buildings=('Square Footage', 'count')
).reset_index()
decade_usage['sqft_millions'] = decade_usage['sqft'] / 1e6

if measure == 'Total square footage':
    y_field = 'sqft_millions:Q'
    y_title = 'Square footage built (millions of sq ft)'
else:
    y_field = 'buildings:Q'
    y_title = 'Number of buildings built'

usage_order = main_usages + ['Other']
usage_select = alt.selection_point(fields=['Usage'], bind='legend')

plot1 = alt.Chart(decade_usage).mark_bar().encode(
    x=alt.X('Decade:O', title='Decade built'),
    y=alt.Y(y_field, title=y_title),
    color=alt.Color('Usage:N', scale=alt.Scale(domain=usage_order, scheme='tableau10'),
                    title='Usage (click to highlight)'),
    order=alt.Order('Usage:N'),
    opacity=alt.condition(usage_select, alt.value(1.0), alt.value(0.15)),
    tooltip=[alt.Tooltip('Decade:O', title='Decade'),
             alt.Tooltip('Usage:N'),
             alt.Tooltip('sqft_millions:Q', title='Sq ft (millions)', format='.2f'),
             alt.Tooltip('buildings:Q', title='Buildings')]
).add_params(
    usage_select
).properties(
    height=420
)

st.altair_chart(plot1)

st.write(
    "**Write-up for Plot 1.** This plot shows how much building space the state of Illinois added in "
    "each decade, split by what the buildings are used for. The main feature I want to highlight is "
    "the big building boom in the 1960s: that decade adds about 21 million sq ft, much more than any "
    "other decade, and the 1970s are second. A lot of this is Assembly, Business and Education space, "
    "and most of the 1960s space belongs to the state universities. You can "
    "also see that Detention & Correction space grows in the 1980s and 1990s, which matches the growth "
    "of the prison system in that period. Switching the radio button to 'Number of buildings' tells a "
    "different story, because Storage and 'Other' buildings are very common but small (for example "
    "sheds at state parks), so they dominate the counts but not the square footage. For the design, I "
    "used bars because the decade is an ordered category and the bar height (a position/length "
    "encoding) is the easiest way to compare amounts. I stacked the bars so the total for each decade "
    "is still readable, and used a categorical color scheme (tableau10) for usage because the "
    "categories have no order. The interactivity is the radio button (a Streamlit widget that changes "
    "the y-axis measure) and a clickable legend: clicking a usage in the legend fades out the other "
    "categories so you can follow one category across decades, which is hard to do in a stacked chart. "
    "If I had more time, I would add an option to show each usage as its own small multiple, because "
    "the categories in the middle of the stack are hard to compare, and I would try to adjust for "
    "buildings that were torn down, since this dataset only includes buildings the state still owns."
)

# ---------------- Plot 2 ----------------
st.header('Plot 2: How old and how big are each agency\'s buildings?')

agency_sizes = clean.groupby('Agency Name')['Square Footage'].sum().sort_values(ascending=False)
agency_list = ['All agencies'] + list(agency_sizes.index)
agency = st.selectbox('Choose an agency:', agency_list, index=1)

if agency == 'All agencies':
    agency_df = clean
else:
    agency_df = clean[clean['Agency Name'] == agency]

st.write(f"{agency}: {len(agency_df):,} buildings, "
         f"{agency_df['Square Footage'].sum() / 1e6:.2f} million sq ft in total, "
         f"median year built {int(agency_df['Year Constructed'].median())}.")

status_order = ['In Use', 'In Progress', 'Abandon']

plot2 = alt.Chart(agency_df).mark_circle(size=40, opacity=0.6).encode(
    x=alt.X('Year Constructed:Q', title='Year built', scale=alt.Scale(domain=[1850, 2020]),
            axis=alt.Axis(format='d')),
    y=alt.Y('Square Footage:Q', title='Square footage (log scale)', scale=alt.Scale(type='log')),
    color=alt.Color('Bldg Status:N', title='Building status',
                    scale=alt.Scale(domain=status_order, range=['#4c78a8', '#f58518', '#e45756'])),
    tooltip=['Location Name', 'City', 'Year Constructed', 'Square Footage', 'Total Floors',
             'Usage', 'Bldg Status']
).properties(
    height=450
)

st.altair_chart(plot2)

st.write(
    "**Write-up for Plot 2.** This plot lets you pick one state agency and see every one of its "
    "buildings, with the year it was built on the x-axis and its size on the y-axis. The feature I want "
    "to highlight is how different the agencies are. The University of Illinois (the default choice, "
    "since it has the most square footage) has mostly large buildings, with the biggest wave of "
    "construction in the 1960s and a smaller group of older buildings from 1900 to 1930. The Department "
    "of Corrections has a clear wave of building in the 1980s and 1990s. The Department of Natural "
    "Resources has over 2,000 very small buildings (under 1,000 sq ft), and it also has the most "
    "abandoned buildings of any agency. For the "
    "design, I used a scatter plot with circle marks because both axes are quantitative and I want to "
    "show individual buildings. I used a log scale on the y-axis because square footage ranges from "
    "under 100 to over 1,000,000 sq ft, and on a linear scale almost every point would be squished at "
    "the bottom. I made the circles partly transparent so overlapping points are still visible. Color "
    "shows building status, using blue for 'In Use' (most buildings) and orange and red for the less "
    "common 'In Progress' and 'Abandon' so they stand out. The x-axis range is fixed so that agencies can "
    "be compared to each other when you switch the dropdown. The interactivity is the Streamlit select "
    "box that filters the data to one agency, plus tooltips with the building name and city. If I had "
    "more time, I would add a second view that maps the buildings by county, and I would let the user "
    "select several agencies at once to compare them in the same plot."
)

# ---------------- HW5 overlap ----------------
st.header('Overlap with Homework #5')
st.write(
    "There is no overlap between this homework and my Homework #5. Homework #5 used the BFRO Bigfoot "
    "sighting reports dataset, while this app uses the Illinois building inventory dataset. Both plots "
    "and all of the text in this app are new and were not copied from Homework #5."
)
