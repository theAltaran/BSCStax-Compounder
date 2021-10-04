##########################################################################
#  BSCStax Compounder v0.1.1a
#  - uses Python3
#  - Install web3 using pip
#  - Really, we haven't tested this on anything but linux or WSL
#  - Use at your own risk
#  - this code is not optimized.  Its hacked together from other scripts
#  - Use at your own risk
#
##########################################################################
import os
import json
import asyncio
import logging
from decimal import Decimal
from urllib.request import urlopen, Request
from web3 import Web3
from web3.middleware import geth_poa_middleware

# Setup logging
log_format = '%(levelname)s:%(asctime)s: %(message)s'

logging.basicConfig(level=logging.INFO,format=log_format)

logging.info('Reading config')

"""" Add your wallet's private Key """
your_wallet_key = '**insertYourWalletKeyHere**'
MinStaxCompound = 1
PollSeconds = 120

compound_pct = Decimal('.01')
# RPC to access Binance Smart Chain
rpc_uri = 'https://bsc-dataseed1.ninicoin.io'

# Contract Info
seekContract = '**insertStaxContractAddressHere**'
abiContract = '[{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"staxBake","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"ceoAddress","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getMyMiners","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"initialized","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"claimedStax","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"rt","type":"uint256"},{"name":"rs","type":"uint256"},{"name":"bs","type":"uint256"}],"name":"calculateTrade","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"sellStax","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"name":"amount","type":"uint256"}],"name":"seedMarket","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"amount","type":"uint256"}],"name":"devFee","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"pure","type":"function"},{"constant":true,"inputs":[],"name":"marketStax","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"eth","type":"uint256"},{"name":"contractBalance","type":"uint256"}],"name":"calculateStaxBuy","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"ref","type":"address"}],"name":"compoundStax","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"contractBalance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"referrals","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getMyStax","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"ref","type":"address"},{"name":"amount","type":"uint256"}],"name":"enterStax","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"eth","type":"uint256"}],"name":"calculateStaxBuySimple","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"staxs","type":"uint256"}],"name":"calculateStaxSell","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"ceoAddress2","outputs":[{"name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"STAX_TO_HATCH","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"staxMiners","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"adr","type":"address"}],"name":"getStaxSinceBake","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"inputs":[],"payable":false,"stateMutability":"nonpayable","type":"constructor"}]'

"""" No need to touch anything after this """

precision = Decimal(1e18)
web3 = Web3(Web3.HTTPProvider(rpc_uri))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

def execute_transaction(call, target_account):
    logging.info(f'\texecute_transaction call={call}, target_account={target_account}')
    nonce = web3.eth.getTransactionCount(target_account.address)
    build = call.buildTransaction({'from': target_account.address, 'nonce': nonce, 'gasPrice': 5000000000})
    sign = target_account.sign_transaction(build)

    args = dict(zip([x['name'] for x in call.abi['inputs']], call.args))
    print(f'{target_account.address}: {call.address} {call.fn_name} with args {str(args)}')
    transaction = web3.eth.sendRawTransaction(sign.rawTransaction)
    if transaction:
        return transaction

account = web3.eth.account.from_key(your_wallet_key)

logging.info(f'\tMy Account: {account.address}')

""" Get the ABI for the existing contracts on BSC"""
pit_address = seekContract
pit_abi = abiContract

pit = web3.eth.contract(pit_address, abi=pit_abi)
#deposit = pit.functions.userInfo(0, account.address).call()[0]
stax = pit.functions.staxMiners(account.address).call()
logging.info(f'\tMy current minters: {stax}')

async def check_for_compound(poll_interval):
    global deposit
    while True:
        pending = pit.functions.getStaxSinceBake(account.address).call()
        sellamount = pit.functions.calculateStaxSell(pending).call()
        NewPending = (sellamount/1000000000000000000)
        # approximation.  close enough...
        pending = (NewPending * 0.95)
        if pending < MinStaxCompound:
            logging.info(f'\tPending [{pending}] less than min [{MinStaxCompound}]')
        else:
            run_compound = pit.functions.compoundStax(account.address)
            txn = execute_transaction(run_compound, account)
            print(web3.eth.waitForTransactionReceipt(txn))     
            stax = pit.functions.staxMiners(account.address).call()
            logging.info(f'\tMy current minters: {stax}')
            
        await asyncio.sleep(poll_interval)

event_handler = asyncio.get_event_loop()

try:
    event_handler.run_until_complete(check_for_compound(PollSeconds))
except KeyboardInterrupt:
    pass
