import streamlit as st   # With streamlit we build a Web App
import pandas as pd # With Pandas we do Data Manipulation
from PIL import Image # With Pillow we open images
import requests # With Requests we send HTTP Requests to retrieve informations
from bs4 import BeautifulSoup # With Beautiful Soup we parse and extract info from a Web Page
from geopy.geocoders import Nominatim # With Geopy we transform City name in Latitude and Longitude
import time # Time
import plotly.express as px # With plotly we do Data Visualization
import concurrent.futures # With Concurrent.futures we enable Multithreading

geolocator = Nominatim(user_agent="myApp", timeout=10) # Initialize Geopy

logo = Image.open('logo.png') # Import logo with Pillow
data_onisep = pd.read_csv('data_onisep_transformed.csv') # We open the CSV File

header = st.container() # Create Streamlit Container

px.set_mapbox_access_token('pk.eyJ1IjoicG9yY29kaW9kb3BwaW8iLCJhIjoiY2wzbXJ5M3BoMDducDNpcGJpZDQ0MXhrNCJ9.h5SiHdVMNCLQk2iH_i7Fog') # Token for MapBox API

# Function to scrap every school at every level in France for a profession
def download_form(link_formation):
    global ecoles # Set Ecoles variable to global
    req = requests.get(link_formation) # Requests.get to retrieve web page based on URL
    soup = BeautifulSoup(req.text, 'html.parser') # BeautifoulSoup will read the web page and parse it
    code = soup.find('div', {'data-ideo-page':'true'}).get('data-context-params').replace('{"formation":','').replace(',"region":null}','') # We retrieve the profession Code with Beautifoul Soup Find and data cleaning
    req2 = requests.get(f'https://www.onisep.fr/recherche/api/html?context=where_to_learn&formation={code}&page=1') # We retrieve data about schools using the profession code and requests
    soup2 = BeautifulSoup(req2.text, 'html.parser') # BeautifoulSoup will read the web page and parse it
    pag = soup2.find('span', {'class':'search-ui-header-pagination-final-number'}) # We scrap maximum page
    if str(type(pag)) == "<class 'bs4.element.Tag'>": # If you found pag scrap multiple pages
        for y in range(1,int(pag.text)): # Scrap all content for every page
            req3 = requests.get(f'https://www.onisep.fr/recherche/api/html?context=where_to_learn&formation={code}&page={y}').text # Requests.get to retrieve web page based on URL
            soup3 = BeautifulSoup(req3, 'html.parser')   # BeautifoulSoup will read the web page and parse it
            table = soup3.find('table') # Scrap table with schools
            links = table.find_all('a') # Inside the table scrap the a tags
            links_final = ['https://www.onisep.fr' + i.get('href') for i in links] # Extract the transform link from A
            text = [i.text.replace('\n','').strip() for i in links]  # Clean the a tag and extract text
            comune = table.find_all('td',{'data-label':'Commune'}) # Retrieve info about Commune
            comune = [i.text for i in comune] # Extract the text from comune
            postal = table.find_all('td',{'data-label':'Code postal'})  # Retrieve info about Code Postal
            postal = [i.text for i in postal] # Extract the text from Postal
            df2 = pd.DataFrame(list(zip(text,links_final,postal,comune)), columns=['name','link','cp','comune']) # Create Dataframe
        ecoles = pd.concat([ecoles,df2]).reset_index(drop=True) # Append to Dataframe Ecoles new dataframe
    else: # Else scrap one page
        req3 = requests.get(f'https://www.onisep.fr/recherche/api/html?context=where_to_learn&formation={code}&page=1').text
        soup3 = BeautifulSoup(req3, 'html.parser')
        table = soup3.find('table')
        links = table.find_all('a')
        links_final = ['https://www.onisep.fr' + i.get('href') for i in links]
        text = [i.text.replace('\n','').strip() for i in links]
        comune = table.find_all('td',{'data-label':'Commune'})
        comune = [i.text for i in comune]
        postal = table.find_all('td',{'data-label':'Code postal'})
        postal = [i.text for i in postal]
        df2 = pd.DataFrame(list(zip(text,links_final,postal,comune)), columns=['name','link','cp','comune'])
        ecoles = pd.concat([ecoles,df2]).reset_index(drop=True).drop_duplicates(subset=['link'])

    return ecoles # Return dataframe containing all schools

with header: # Initiziale Streamlit container
    st.image(logo) # load and display logo
    inp_feature = st.text_input('Insérer une compétence ou un métier',"").lower() # Input box
    data = data_onisep[data_onisep['description'].str.contains(f'(?=.*{inp_feature} )')].reset_index(drop=True) # Search Input in Dataframe Description

    if len(data) >= 1: # If column data len superior to 1
        data = data_onisep[data_onisep['description'].str.contains(f'(?=.*{inp_feature} )')].reset_index(drop=True)
    else: # Else search in name
        data = data_onisep[data_onisep['libellé métier'].str.contains(f'(?=.*{inp_feature})')].reset_index(drop=True)

    sel = st.selectbox('Sélectionnez un métier', options=[i for i in data['libellé métier']], index=0) # Select box containing profession of data frame
    sel_inp = st.text(str(sel)) # Extract selection

    links = data_onisep[data_onisep['libellé métier'].str.contains(f'(?=.*{sel})')].reset_index(drop=True) # Create Dataframe with selected profession
    link = links['lien site onisep.fr'][0] # Extract link profession

    # Scrap Infos about profession
    r = requests.get(link).text
    soup = BeautifulSoup(r, 'html.parser')
    text = soup.find('div', {'id' : 'les-formations-et-les-diplomes'})
    links = text.find_all('a')
    formations = ['https://www.onisep.fr' + str(x.get('href')) for x in links][1:]
    level = [x.replace('https://www.onisep.fr/Ressources/Univers-Formation/Formations/','').split("/",1)[0] for x in formations]
    nom_f = [x.replace('https://www.onisep.fr/Ressources/Univers-Formation/Formations/','').replace('-',' ').split("/",1)[1] for x in formations]
    description_f = text.find_all('p')
    description_f = [x.text for x in description_f]

    # For loop to display all description on Streamlit
    for i in description_f:
        st.markdown(i)

    # If button is pressed:
    if st.button('Chercher une école'):

        st.text('Scraping en cours... Cela peut prendre quelques minutes...') # Prin text

        # Create dataframe with formations
        form = pd.DataFrame(list(zip(nom_f,formations)), columns=['nom','lien'])
        form = form[form['lien'] != 'https://www.onisep.frNone'] # Filter dataframe
        form_l = [x for x in form.lien.values] # Extract formations links

        ecoles = pd.DataFrame(columns=['name','link','cp','comune']) # Initialize empty dataframe

        # Use multithreading to optimize Download Form function
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(download_form, link_formation) for link_formation in form_l} # For loop containing links

            for fut in concurrent.futures.as_completed(futures):
                fut.result()

        # For every city in DF ecoles find Longitude and Latitude
        ecoles[['lat', 'lon']] = ecoles['comune'].apply(geolocator.geocode).apply(lambda x: pd.Series([x.latitude, x.longitude], index=['lat', 'lon']))

        st.markdown(f'Ecoles pour {str(sel)}')

        # Plot scatter map using Mapbox API
        fig = px.scatter_mapbox(ecoles,lat='lat',lon='lon', hover_name="name",hover_data=['cp','comune'] , template='plotly_dark', width=800, height=400)
        fig.update_geos(fitbounds=False)
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)

    else:
        time.sleep(3)

