import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
import time
import plotly.express as px

geolocator = Nominatim(user_agent="myApp", timeout=10)

logo = Image.open('logo.png')
data_onisep = pd.read_csv('data_onisep_transformed.csv')

header = st.container()
dataset = st.container()
features = st.container()
model_training = st.container()


with header:
    st.image(logo)
    inp_feature = st.text_input('Insérer une compétence ou un métier',"").lower()
    data = data_onisep[data_onisep['description'].str.contains(f'(?=.*{inp_feature} )')].reset_index(drop=True)

    if len(data) >= 1:
        data = data_onisep[data_onisep['description'].str.contains(f'(?=.*{inp_feature} )')].reset_index(drop=True)
    else:
        data = data_onisep[data_onisep['libellé métier'].str.contains(f'(?=.*{inp_feature})')].reset_index(drop=True)

    sel = st.selectbox('Sélectionnez un métier', options=[i for i in data['libellé métier']], index=0)
    sel_inp = st.text(str(sel))

    links = data_onisep[data_onisep['libellé métier'].str.contains(f'(?=.*{sel})')].reset_index(drop=True)
    link = links['lien site onisep.fr'][0]

    # Scrap Infos
    r = requests.get(link).text
    soup = BeautifulSoup(r, 'html.parser')
    text = soup.find('div', {'id' : 'les-formations-et-les-diplomes'})
    links = text.find_all('a')
    formations = ['https://www.onisep.fr' + str(x.get('href')) for x in links][1:]
    level = [x.replace('https://www.onisep.fr/Ressources/Univers-Formation/Formations/','').split("/",1)[0] for x in formations]
    nom_f = [x.replace('https://www.onisep.fr/Ressources/Univers-Formation/Formations/','').replace('-',' ').split("/",1)[1] for x in formations]
    description_f = text.find_all('p')
    description_f = [x.text for x in description_f]

    for i in description_f:
        st.markdown(i)

    if st.button('Chercher une école'):

        st.text('Scraping en cours... Cela peut prendre quelques minutes...')

        form = pd.DataFrame(list(zip(nom_f,formations)), columns=['nom','lien'])
        form = form[form['lien'] != 'https://www.onisep.frNone']
        form_l = [x for x in form.lien.values]

        ecoles = pd.DataFrame(columns=['name','link','cap','comune'])

        for i in range(len(form_l)):
            req = requests.get(form_l[i])
            soup = BeautifulSoup(req.text, 'html.parser')
            code = soup.find('div', {'data-ideo-page':'true'}).get('data-context-params').replace('{"formation":','').replace(',"region":null}','')
            req2 = requests.get(f'https://www.onisep.fr/recherche/api/html?context=where_to_learn&formation={code}&page=1')
            soup2 = BeautifulSoup(req2.text, 'html.parser')
            pag = soup2.find('span', {'class':'search-ui-header-pagination-final-number'})
            if str(type(pag)) == "<class 'bs4.element.Tag'>":
                for x in range(1,int(pag.text)):
                    req3 = requests.get(f'https://www.onisep.fr/recherche/api/html?context=where_to_learn&formation={code}&page={x}').text
                    soup3 = BeautifulSoup(req3, 'html.parser')
                    table = soup3.find('table')
                    links = table.find_all('a')
                    links_final = ['https://www.onisep.fr' + i.get('href') for i in links]
                    text = [i.text.replace('\n','').strip() for i in links]
                    comune = table.find_all('td',{'data-label':'Commune'})
                    comune = [i.text for i in comune]
                    postal = table.find_all('td',{'data-label':'Code postal'})
                    postal = [i.text for i in postal]
                    df2 = pd.DataFrame(list(zip(text,links_final,postal,comune)), columns=['name','link','cap','comune'])
                ecoles = pd.concat([ecoles,df2]).reset_index(drop=True)
            else:
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
                df2 = pd.DataFrame(list(zip(text,links_final,postal,comune)), columns=['name','link','cap','comune'])
                ecoles = pd.concat([ecoles,df2]).reset_index(drop=True)

        ecoles[['lat', 'lon']] = ecoles['comune'].apply(geolocator.geocode).apply(lambda x: pd.Series([x.latitude, x.longitude], index=['lat', 'lon']))

        st.markdown(f'Ecoles pour {str(sel)}')

        fig = px.scatter_geo(ecoles,lat='lat',lon='lon', hover_name="name",hover_data=['cap','comune'] , template='plotly_dark', width=800, height=400)
        st.plotly_chart(fig, use_container_width=True)

    else:
        time.sleep(3)

