import requests
import json
import time
import math
import re
from prettytable import PrettyTable
from binance.client import Client
from binance.exceptions import BinanceAPIException
from sys import exit
from decimal import Decimal
import ccxt

# Sustituye 'tu_access_key' y 'tu_secret_key' por tus credenciales reales
access_key = ''
secret_key = ''
test_access_key = ''
test_secret_key = ''
global client
Symbol_Base = "USDT"
Capital_Inicial = 20.1
USE_TESNET = True
OnlineMode = True
cada_segundos = 100
Repetir = True
UsarBNB = False
GananciaTotal = 0

def GetPresicion(symbol, cantidad, price):
    if OnlineMode:
        info = client.get_symbol_info(symbol)
        # # Obtener los datos de LOT_SIZE para el símbolo dado
        min_qty = [Decimal(_['minQty']) for _ in info['filters'] if _['filterType'] == 'LOT_SIZE'][0]
        max_qty  = [Decimal(_['maxQty']) for _ in info['filters'] if _['filterType'] == 'LOT_SIZE'][0]
        step_size = [Decimal(_['stepSize']) for _ in info['filters'] if _['filterType'] == 'LOT_SIZE'][0]
        minNotional = [Decimal(_['minNotional']) for _ in info['filters'] if _['filterType'] == 'NOTIONAL'][0]
        cantidad = (Decimal(cantidad) // step_size) * step_size
        # Ensure quantity is within allowed range
        cantidad = max((min_qty), min(cantidad, (max_qty)))        
    return cantidad

def test_api_key(client, BinanceAPIException):
    """Checks to see if API keys supplied returns errors

    Args:
        client (class): binance client class
        BinanceAPIException (clas): binance exeptions class

    Returns:
        bool | msg: true/false depending on success, and message
    """
    try:
        client.get_account()
        return True, "API key validated succesfully"
    
    except BinanceAPIException as e:         
        if e.code in  [-2015,-2014]:
            bad_key = "Your API key is not formatted correctly..."
            america = "If you are in america, you will have to update the config to set AMERICAN_USER: True"
            ip_b = "If you set an IP block on your keys make sure this IP address is allowed. check ipinfo.io/ip"
            
            msg = f"Your API key is either incorrect, IP blocked, or incorrect tld/permissons...\n  most likely: {bad_key}\n  {america}\n  {ip_b}"

        elif e.code == -2021:
            issue = "https://github.com/CyberPunkMetalHead/Binance-volatility-trading-bot/issues/28"
            desc = "Ensure your OS is time synced with a timeserver. See issue."
            msg = f"Timestamp for this request was 1000ms ahead of the server's time.\n  {issue}\n  {desc}"
        elif e.code == -1021:
            desc = "Your operating system time is not properly synced... Please sync ntp time with 'pool.ntp.org'"
            msg = f"{desc}\nmaybe try this:\n\tsudo ntpdate pool.ntp.org"
        else:
            msg = "Encountered an API Error code that was not caught nicely, please open issue...\n"
            msg += str(e)

        return False, msg
    
    except Exception as e:
        return False, f"Fallback exception occured:\n{e}"
        
def CrearConeccionBinance():
    global client
    if OnlineMode:
        if USE_TESNET:
           client = Client(test_access_key, test_secret_key) 
        else:
            client = Client(access_key, secret_key)
        if USE_TESNET:         
            client.API_URL = 'https://testnet.binance.vision/api'
            # If the users has a bad / incorrect API key.
            # this will stop the script from starting, and display a helpful error.
            api_ready, msg = test_api_key(client, BinanceAPIException)
            if api_ready is not True:
                exit(f'{msg}') 
            
def GetLastOrderInfo(symbol1):
    if OnlineMode:
        orders = client.get_all_orders(symbol=symbol1, limit=1)
        # Iterar sobre cada pedido en la lista
        for order in orders:    
            # Si quieres acceder a campos específicos del pedido, puedes hacerlo así:
            order_id = order['orderId']
            symbol = order['symbol']
            monto = order["origQty"]
            status = order['status']
            Cumulative = order["cummulativeQuoteQty"]
            # y así sucesivamente para cada campo disponible en el diccionario
            print(f"\t \t Order ID: {order_id}, Symbol: {symbol}, Monto: {monto} ,Status: {status}") #, Cumulative: {Cumulative}")
        
while Repetir:
    CrearConeccionBinance()
    # Define la dirección URL de la API de Binance
    url = "https://api.binance.com/api/v3/ticker/bookTicker"

    # Realiza una solicitud GET a la API de Binance
    response = requests.get(url)

    # Verifica si la solicitud fue exitosa
    if response.status_code == 200:
        # Obtiene los datos de precios en formato JSON
        prices = response.json()

    all_prices = [price for price in prices]
    bol_prices = [price for price in prices if price["symbol"].endswith(Symbol_Base)]

    # Analiza cada combinación de tres criptomonedas para determinar si existe una oportunidad de arbitraje
    for i in range(len(bol_prices)):
        for j in range(i + 1, len(all_prices)):
            for k in range(j + 1, len(bol_prices)):
                # Obtiene los precios de compra y venta de la primera criptomoneda
                symbol1 = bol_prices[i]["symbol"]
                bid_price1 = float(bol_prices[i]["bidPrice"])
                ask_price1 = float(bol_prices[i]["askPrice"])

                # Obtiene los precios de compra y venta de la segunda criptomoneda
                symbol2 = all_prices[j]["symbol"]
                bid_price2 = float(all_prices[j]["bidPrice"])
                ask_price2 = float(all_prices[j]["askPrice"])

                # Obtiene los precios de compra y venta de la tercera criptomoneda
                symbol3 = bol_prices[k]["symbol"]
                bid_price3 = float(bol_prices[k]["bidPrice"])
                ask_price3 = float(bol_prices[k]["askPrice"])                
                
                
                # Verifica si el primer símbolo comienza con "USDT" y el tercer símbolo termina con "USDT"
                if symbol1.endswith(Symbol_Base) and symbol2.endswith(symbol1.replace(Symbol_Base, "")) and symbol3.startswith(symbol2.replace(symbol1.replace(Symbol_Base, ""),"")) and ask_price2!=0 and ask_price3!=0 and bid_price1!=0:
                           #BTCUSDT   		         LTCBTC   		           LTCUSDT 
                    #COMPRO BTC con USDT     COMPRAR LTC con BTC      VENDER LTC obtengo USDT

                    
                    Compra1 = float(Capital_Inicial) / bid_price1 #BTC
                    Comisionbnb1 = Compra1 * 0.00075
                    Comision1 = Compra1 * 0.001
                    if not UsarBNB and not OnlineMode: Compra1 = Compra1 - Comision1

              
                    Compra2 = Compra1 / bid_price2 #LTC
                    Comisionbnb2 = Compra2 * 0.00075
                    Comision2 = Compra2 * 0.001
                    if not UsarBNB and not OnlineMode: Compra2 = Compra2 - Comision2
                    
                    
                    Venta1 = Compra2 #* ask_price3 #USDT
                    Comisionbnb3 = Venta1 * 0.00075
                    Comision3 = Venta1 * 0.001
                    if not UsarBNB and not OnlineMode: Venta2 =  Venta2 - Comision3                     
                    
                    Ganancia1 = (Venta1 * ask_price3) - Capital_Inicial

                    if Ganancia1 > 0.10 and Ganancia1 < 100.0: 
                        print("\n")
                        print("Existe una oportunidad de arbitraje entre", symbol1, symbol2, symbol3, "con una ganancia de", Ganancia1)
                        
                        print("\t Comprando ", symbol1, "Cantidad: ", Compra1, GetPresicion(symbol1, Compra1, bid_price1))
                        if OnlineMode:
                            order_details = client.create_order( 
                                symbol = symbol1,
                                side = 'BUY',
                                type = 'MARKET',
                                quantity = GetPresicion(symbol1, Compra1, bid_price1)
                            )
                            GetLastOrderInfo(symbol1)
                        
                        print("\t Comprando ", symbol2, "Cantidad: ", Compra2 ,GetPresicion(symbol2, Compra2, bid_price2))
                        if OnlineMode:
                            order_details = client.create_order( 
                                symbol = symbol2,
                                side = 'BUY',
                                type = 'MARKET',
                                quantity = GetPresicion(symbol2, Compra2, bid_price2)
                            )
                            GetLastOrderInfo(symbol2)
                        #print("Balance: ", client.get_asset_balance(asset=symbol2.replace(symbol1.replace(Symbol_Base, ""), "")), "Compra-Comision1: ", Compra1 - Comision1)
                        
                        print("\t Vendiendo ", symbol3, "Cantidad: ", Venta1, GetPresicion(symbol3, Venta1, ask_price3))
                        if OnlineMode:
                            order_details = client.create_order( 
                                symbol = symbol3,
                                side = 'SELL',
                                type = 'MARKET',
                                quantity = GetPresicion(symbol3, Venta1, ask_price3)
                            )
                            GetLastOrderInfo(symbol3)
                       
                        
                        ComisionTotal = Comisionbnb1 + Comisionbnb1 + Comisionbnb1
                                
                        GananciaTotal = GananciaTotal + Ganancia1
                        print("\n GANANCIA TOTAL DEL BOT:", GananciaTotal )
    print("\n")
    if Repetir: 
        if cada_segundos > 0:
            print("Esperando ", cada_segundos, " segundos")
            time.sleep(cada_segundos)
    else: 
        Repetir = False
