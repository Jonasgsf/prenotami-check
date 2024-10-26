# main.py

import os
import sys
import json
import requests
import fake_useragent
import time
import pytz
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By

# Carrega a configuração do arquivo source.json
SRC_FILE = "source.json"
with open(SRC_FILE, 'r') as f:
    SRC = json.load(f)

def writeDataToFile(file_path, text):
    with open(file_path, "w") as file:
        file.write(text)

def updateCookies():
    try:
        headers = {
            "User-Agent": fake_useragent.UserAgent().random
        }
        authData = {
            "Email": "seu_email@example.com",
            "Password": "sua_senha"
        }

        session = requests.Session()
        authResponse = session.post(SRC["urlAuth"], headers=headers, data=authData)
        if authResponse.status_code == 200:
            SRC["cookies"] = session.cookies.get_dict()
            SRC["cookiesModified"] = SRC["lastRequestDate"]
            print("Cookies atualizados com sucesso.")
        else:
            print(f"Falha na autenticação. Código de status: {authResponse.status_code}")
    except Exception as e:
        print(f"Erro ao atualizar cookies: {e}")

def getVisa():
    try:
        headers = {
            "User-Agent": fake_useragent.UserAgent().random
        }
        session = requests.Session()

        # Verifica se os cookies precisam ser atualizados
        if not SRC["cookiesModified"]:
            print("Data de cookiesModified está vazia. Atualizando cookies.")
            updateCookies()
        else:
            delta_seconds = (
                datetime.strptime(SRC["lastRequestDate"], SRC["timeFormat"]) -
                datetime.strptime(SRC["cookiesModified"], SRC["timeFormat"])
            ).total_seconds()
            if delta_seconds > SRC["refreshEvery"] or delta_seconds < 0 or not SRC["cookies"]:
                print("Cookies estão desatualizados ou vazios. Atualizando cookies.")
                updateCookies()

        response = session.get(SRC["urlVisa"], headers=headers, cookies=SRC["cookies"])
        print(f"Resposta recebida com código de status {response.status_code}")
        writeDataToFile("response.html", response.text)

        return response.text
    except Exception as e:
        print(f"Erro ao obter informações de visto: {e}")
        return ""

def sendNotification():
    try:
        text = (SRC.get('notificationText', 'Notificação enviada em {0}')).format(SRC["lastRequestDate"])
        print("Enviando notificação...")

        for number in SRC["phones"]:
            command = f'''
            curl -X POST https://api.twilio.com/2010-04-01/Accounts/{SRC["sid"]}/Messages.json \
            --data-urlencode "Body={text}" \
            --data-urlencode "From={SRC['numberFrom']}" \
            --data-urlencode "To={number}" \
            -u {SRC["sid"]}:{SRC["token"]}
            '''
            os.system(command)

        print("Notificação enviada com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar notificação: {e}")

def fillClientData():
    try:
        # Carrega os dados dos clientes da planilha Excel
        df = pd.read_excel('clientes.xlsx')

        # Inicializa o Selenium WebDriver (usando o Chrome neste exemplo)
        driver = webdriver.Chrome(executable_path='/caminho/para/chromedriver')

        for index, client in df.iterrows():
            # Navega até a página de reserva
            driver.get(SRC["urlReservation"])

            # Preenche os dados do cliente
            # Substitua 'element_id' pelos IDs ou XPaths reais dos campos do formulário
            driver.find_element(By.ID, 'name_field').send_keys(client['Nome'])
            driver.find_element(By.ID, 'passport_field').send_keys(client['Passaporte'])
            # Preencha outros campos necessários aqui

            # Submete o formulário
            driver.find_element(By.ID, 'submit_button').click()

            print(f"Reserva submetida para {client['Nome']}.")

            # Aguarde ou verifique se necessário

        driver.quit()
    except Exception as e:
        print(f"Erro ao preencher dados do cliente: {e}")

def main():
    while True:
        SRC["lastRequestDate"] = datetime.now(pytz.timezone(SRC["tz"])).strftime(SRC["timeFormat"])
        response = getVisa()

        if SRC["phrase"] in response:
            print("Vaga não disponível. Verificando novamente em 2 minutos.")
            time.sleep(120)  # Aguarda 2 minutos antes de verificar novamente
        else:
            print("Vaga disponível!")
            fillClientData()
            sendNotification()
            break  # Sai do loop após processar

        # Atualiza o arquivo SRC com os dados mais recentes
        with open(SRC_FILE, 'w') as f:
            json.dump(SRC, f, indent=4)

if __name__ == "__main__":
    main()
