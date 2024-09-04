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

# Sustituye 'access_key' y 'secret_key' por tus credenciales reales
access_key = 'SIbij3U0FZ8QOdq6NOXGL1BTTpGwioVnO0bAwkKXFWmWGqaTz0vSp28w67ED151U'
secret_key = 'l4Idg85lRDDNL6oEamKf8me7ZkfkJidi0FS31WkDof4jafVrWDfgreyFc3V2NefE'
#acceder a https://testnet.binance.vision/
test_access_key = 'Un7s7fZ1hfhKJcTIyNCvbqUinBePlmaP5oSNbovz95faXiTOCbt7d4fUaRdZftmU'
test_secret_key = 'Vhk1FQBpBu8UXNf7lpTtcIULE3AlbZ7RlRDVGcUXmjdC1HxbDzGusCvGPCitXhyY'

global client
Symbol_Base = "USDT"
Capital_Inicial = 21
USE_TESNET = True
OnlineMode = True
cada_segundos = 100
Repetir = True
UsarBNB = False
GananciaTotal = 0
OrderIdSaveFile = "Orders.txt"
DescuentoComisionBNB = 0.00075
DescuentoComision = 0.001

def GetPresicion(symbol, monto):
    canitdad = 0
    if OnlineMode:
        info = client.get_symbol_info(symbol)
        min_qty = [Decimal(_['minQty']) for _ in info['filters'] if _['filterType'] == 'LOT_SIZE'][0]
        max_qty  = [Decimal(_['maxQty']) for _ in info['filters'] if _['filterType'] == 'LOT_SIZE'][0]
        step_size = [Decimal(_['stepSize']) for _ in info['filters'] if _['filterType'] == 'LOT_SIZE'][0]
        #minNotional = [Decimal(_['minNotional']) for _ in info['filters'] if _['filterType'] == 'NOTIONAL'][0]
        cantidad = (Decimal(monto) // step_size) * step_size
        # Ensure quantity is within allowed range
        cantidad = Decimal(max((min_qty), min(cantidad, (max_qty))))
    else:
        cantidad = round(canitdad, 3)
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
            with open(OrderIdSaveFile, "a") as archivo:
                archivo.write(str(order_id) + " " + symbol + " " + str(monto) + " " + status)

if __name__ == '__main__':
    ComisionTotal = 0
    ComisionTotalbnb = 0
    Capital_Inicial = Decimal(Capital_Inicial)
    DescuentoComision = Decimal(DescuentoComision)
    DescuentoComisionBNB = Decimal(DescuentoComisionBNB)
    
    print("\nInciando Bot Binance - Arbitraje Triangular...\n")
    #print("\nSe usara la siguiente configuracion: Symbol_Base", Symbol_Base, "con Capital_Inicial", Capital_Inicial, "Repetir el bot", Repetir, "\n")

    if USE_TESNET == False and OnlineMode == True:
        print("Esta a punto de usar el bot con su capital real de criptomonedas...")
        print("Se esperara 10 segundos antes de continuar. Ctrl C para detener el bot..")
        time.sleep(10)
           
        
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
                    bid_price1 = Decimal(bol_prices[i]["bidPrice"])
                    ask_price1 = Decimal(bol_prices[i]["askPrice"])

                    # Obtiene los precios de compra y venta de la segunda criptomoneda
                    symbol2 = all_prices[j]["symbol"]
                    bid_price2 = Decimal(all_prices[j]["bidPrice"])
                    ask_price2 = Decimal(all_prices[j]["askPrice"])

                    # Obtiene los precios de compra y venta de la tercera criptomoneda
                    symbol3 = bol_prices[k]["symbol"]
                    bid_price3 = Decimal(bol_prices[k]["bidPrice"])
                    ask_price3 = Decimal(bol_prices[k]["askPrice"])                
                    
                    #   _________________________
                    #  |                        |
                    #  |                        v
                    #+------+------+  +------+------+  +------+------+
                    #|PART1 | PART2|  |PART1 | PART2|  |PART1 | PART2|
                    #+------+------+  +------+------+  +------+------+
                    #          |         |                ^      ^
                    #          |         |________________|      |
                    #          |_________________________________|
                    
                    symbol1_part2 = Symbol_Base
                    symbol1_part1 = symbol1.replace(symbol1_part2, "")
                    
                    symbol2_part2 = symbol1_part1
                    symbol2_part1 = symbol2.replace(symbol2_part2, "")
                    
                    symbol3_part2 = symbol1_part2
                    symbol3_part1 = symbol2_part1
                                        
                                        
                    # Verifica si el primer símbolo termina con "USDT" y el tercer símbolo termina con "USDT"   #falta mejorar este filtro
                    if symbol1.endswith(Symbol_Base) and symbol2.endswith(symbol1.replace(Symbol_Base, "")) and symbol3.startswith(symbol2.replace(symbol1.replace(Symbol_Base, ""),"")) and ask_price2!=0 and ask_price3!=0 and bid_price1!=0:
                    #if symbol1.endswith(Symbol_Base) and symbol1_part1 in symbol2 and symbol3.replace(symbol2_part1, "") == Symbol_Base and ask_price2!=0 and ask_price3!=0 and bid_price1!=0:
                               #BTCUSDT   		         LTCBTC   		           LTCUSDT 
                        #COMPRO BTC con USDT     COMPRAR LTC con BTC      VENDER LTC obtengo USDT
                        
                        #DE AQUI <==== calculo estimativo de lo que se podria ganar
                        Compra1 = Capital_Inicial / bid_price1 #BTC                       
                        if UsarBNB: 
                            Comisionbnb1 = Compra1 * DescuentoComisionBNB
                        else:
                            Comision1 = Compra1 * DescuentoComision
                            Compra1 = Compra1 - Comision1

                  
                        Compra2 = Compra1 / bid_price2 #LTC
                        if UsarBNB:
                            Comisionbnb2 = Compra2 * DescuentoComisionBNB
                        else:    
                            Comision2 = Compra2 * DescuentoComision
                            Compra2 = Compra2 - Comision2                           
                        
                        
                        Venta1 = Compra2 #* ask_price3 #USDT
                        if UsarBNB:
                            Comisionbnb3 = Venta1 * DescuentoComisionBNB
                        else:
                            Comision3 = Venta1 * DescuentoComision
                            Venta1 =  Venta1 - Comision3                     
                        
                        Ganancia1 = (Venta1 * ask_price3) - Capital_Inicial
                        #HASTA AQUI <======
                        
                        #el filtro que no anda bien deja pasar monedas parecidas y con montos enormes
                        if Ganancia1 > 0.10 and Ganancia1 <= 1.0: 
                            print("\n")
                            print("Existe una oportunidad de arbitraje entre", symbol1, symbol2, symbol3, "con una ganancia estimativa de", round(Ganancia1, 3))   
                        
                            #DESDE AQUI <==== CALCULO PRECISO DE CADA OPERACION
                            Compra1 = Capital_Inicial / bid_price1 #BTC
                            if UsarBNB: 
                                Comisionbnb1 = Compra1 * DescuentoComisionBNB 
                            else: 
                                presicion1 = GetPresicion(symbol1, Compra1)
                                Comision1 = presicion1 * DescuentoComision
                                Compra1 = presicion1 - Comision1
                                
                      
                            Compra2 = Compra1 / bid_price2 #LTC
                            if UsarBNB: 
                                Comisionbnb2 = Compra2 * DescuentoComisionBNB
                            else: 
                                presicion2 = GetPresicion(symbol2, Compra2)
                                Comision2 = presicion2 * DescuentoComision
                                Compra2 = presicion2 - Comision2
                                
                            
                            Venta1 = Compra2 #* ask_price3 #USDT
                            if UsarBNB: 
                                Comisionbnb3 = Venta1 * DescuentoComisionBNB
                            else:
                                presicion3 = GetPresicion(symbol3, Venta1)
                                Comision3 = presicion3 * DescuentoComision
                                Venta1 =  presicion3 - Comision3  
                            #HASTA AQUI <=======
                            
                            try: 
                                if OnlineMode:                                
                                    print("\t Comprando ", symbol1, "Cantidad: ", presicion1, symbol2_part2)
                                    order_details = client.create_order( 
                                        symbol = symbol1,
                                        side = 'BUY',
                                        type = 'MARKET',
                                        quantity = presicion1
                                    )
                                    GetLastOrderInfo(symbol1)
                                    #print("\t Balance:", client.get_asset_balance(asset=symbol2_part2)['free'], symbol2_part2)
                            except Exception as e:
                                print("\n \t" + str(e))
                                exit(1)
                                 
                            try:
                                print("\t Comprando ", symbol2, "Cantidad: ", presicion2, symbol2_part1)
                                if OnlineMode:
                                    order_details = client.create_order( 
                                        symbol = symbol2,
                                        side = 'BUY',
                                        type = 'MARKET',
                                        quantity = presicion2
                                    )
                                    GetLastOrderInfo(symbol2)
                                    #print("\t Balance:", client.get_asset_balance(asset=symbol2_part1)['free'], symbol2_part1)
                            except Exception as e:
                                print("\n \t" + str(e))
                                exit(1)
                                
                            try:
                                print("\t Vendiendo ", symbol3, "Cantidad: ", presicion3, symbol3_part1)
                                if OnlineMode:
                                    order_details = client.create_order( 
                                        symbol = symbol3,
                                        side = 'SELL',
                                        type = 'MARKET',
                                        quantity = presicion3
                                    )
                                    GetLastOrderInfo(symbol3)
                                    #print("Balance:", client.get_asset_balance(asset=Symbol_Base)['free'], Symbol_Base)
                            except Exception as e:
                                print("\n \t" + str(e))
                                exit(1)
                                 
                            GananciaTotal = GananciaTotal + Ganancia1
                            if UsarBNB:
                                ComisionTotal = ComisionTotal + ComisionTotalbnb
                                print("\nGANANCIA TOTAL DEL BOT:", round(GananciaTotal, 3), "COMISION TOTAL GASTADA:", round(ComisionTotal,3))
                            else:    
                                print("\nGANANCIA TOTAL DEL BOT:", round(GananciaTotal, 3))
        print("\n")
        print("\n")
        if Repetir: 
            print("Esperando ", cada_segundos, " segundos")
            time.sleep(cada_segundos)