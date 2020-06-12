import pytest
import subprocess
import time
import os
import json
import numpy as np
from enum import Enum
from web3 import Web3, HTTPProvider, IPCProvider
from web3.middleware import geth_poa_middleware

STEP_MINIMUM = 0

STEP_MINT = 0
STEP_ENTER = 1
STEP_EXIT = 2
STEP_CHILD_DUMMY_TRANSACTION = 3
STEP_ROOT_TRANSFER = 4
STEP_CHILD_TRANSFER = 5

STEP_MAXIMUM = 5

operator = "0x5E3230019fEd7aB462e3AC277E7709B9b2716b4F"

class ChainInfo:
    def __init__(self, ipc_path, accounts):
        self.ipc_path = ipc_path
        self.instance = None
        self.w3 = Web3(IPCProvider(ipc_path))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        for address in accounts:
            self.w3.geth.personal.unlock_account(address, "", 0)

        self.deploy_token()

    def deploy_token(self):
        compiled_file = "RequestableSimpleToken.json"
        compiled_data = None
        with open(compiled_file) as f:
            compiled_data = json.load(f)

        instance = self.w3.eth.contract(abi= compiled_data['abi'], bytecode= compiled_data['bytecode'])
        tx_hash = instance.constructor().transact({'from': operator})

        print(f"deploy tx : {tx_hash.hex()}")

        self.w3.eth.waitForTransactionReceipt(tx_hash.hex())
        receipt = self.w3.eth.getTransactionReceipt(tx_hash.hex())
        print(f"contract address : {receipt['contractAddress']}")
        self.token_address = receipt["contractAddress"]
        self.instance = self.w3.eth.contract(abi= compiled_data['abi'], address=self.token_address)

        return self.instance

    def faucet_token(self, accounts):
        #for i in range(int(len(accounts)/2)):
        for i in range(len(accounts)):
            tx_hash = self.instance.functions.mint(accounts[i], 1000000000).transact({"from": operator})
            self.w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(self.w3, tx_hash)

    def faucet_ether(self, accounts):
        for account in accounts:
            tx_hash = self.w3.eth.sendTransaction({"from": operator, "to": account, "value": 1000000000000000})
            self.w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(self.w3, tx_hash)

def int_to_bytes(value):
    data = format(value, "x")
    return "0" * (64 - len(data)) + data

@pytest.fixture(scope="session")
def generator():
    np.random.seed(int(time.time()))
    ops = np.random.randint(STEP_MINIMUM, STEP_MAXIMUM, 100)
    return ops

@pytest.fixture(scope="session")
def run_chains():
    RUN_ROOTCHAIN_DIR = "rootchain"
    RUN_CHILDCHAIN_DIR = "childchain"
    RUN_ROOTCHAIN_PATH = "./run.rootchain.sh"
    RUN_CHILDCHAIN_PATH = "./reset.sh"

    log_rootchain = open("log.rootchain", "w")
    log_childchain = open("log.childchain", "w")

    wd = os.getcwd()
    os.chdir(RUN_ROOTCHAIN_DIR)
    root_chain = subprocess.Popen([RUN_ROOTCHAIN_PATH], stderr=log_rootchain)
    time.sleep(20)
    os.chdir(wd)
    os.chdir(RUN_CHILDCHAIN_DIR)
    child_chain = subprocess.Popen([RUN_CHILDCHAIN_PATH], stderr=log_childchain)
    os.chdir(wd)
    time.sleep(60)
    yield [root_chain, child_chain]
    root_chain.kill()
    child_chain.kill()

@pytest.fixture(scope="session")
def accounts():
    return ["0x5E3230019fEd7aB462e3AC277E7709B9b2716b4F", "0x515B385bDc89bCc29077f2B00a88622883bfb498", "0xC927A0CF2d4a1B59775B5D0A35ec76d099e1FaD4", "0x48aFf0622a866d77651eAaA462Ea77b5F39D0ae1", "0xb715125A08140AEA83588a4b569599cde4a0a336", "0x499De281cd965781F1422b7cB73367C15DC416D2", "0xaA60af9BD19dc7438fd19457955C52982D070D27", "0x37da08b6Cd15c3aE905A25Df57B6841A5D80aC93", "0xec4A610a07e81264e8f7F1CAeAe522fEdD7e59c1"]

@pytest.fixture(scope="session")
def chains(run_chains, accounts):
    rootchain_ipc_path = "rootchain/root-chain-node-1/geth.ipc"
    operator_ipc_path = "childchain/.pls.staking/operator1/geth.ipc"

    w3_rootchain = ChainInfo(rootchain_ipc_path, accounts)
    w3_childchain = ChainInfo(operator_ipc_path, accounts)
    w3_rootchain.faucet_token(accounts)
    w3_childchain.faucet_ether(accounts)
    return [w3_rootchain, w3_childchain]

@pytest.fixture(scope="session")
def rootchain_instance(chains):
    rootchain_compiled_file = "RootChain.json"
    rootchain_addr = "0xC4BF071B54914221cC047F480293231E7DF9F85B"

    rootchain_compiled_data = None
    with open(rootchain_compiled_file) as f:
        rootchain_compiled_data = json.load(f)
    rootchain_instance = chains[0].w3.eth.contract(abi= rootchain_compiled_data['abi'], address=rootchain_addr)
    return rootchain_instance

def check_transaction_status(w3, tx_hash):
    receipt = w3.eth.getTransactionReceipt(tx_hash.hex())
    assert receipt["status"] == 1

def print_balance(w3s, instances, address):
    root_balance = w3s[0].eth.getBalance(address)
    child_balance = w3s[1].eth.getBalance(address)
    root_token_balance = instances[0].functions.balances(address).call()
    child_token_balance = instances[1].functions.balances(address).call()
    print(f"# balance of {address} : {root_balance}, {child_balance}, {root_token_balance}, {child_token_balance}")

def test_requestable_random(chains, rootchain_instance, generator, accounts):
    tx_hash = rootchain_instance.functions.mapRequestableContractByOperator(chains[0].token_address, chains[1].token_address).transact({"from": operator})
    print(f"mapping address tx : {tx_hash.hex()}")
    chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
    receipt = chains[0].w3.eth.getTransactionReceipt(tx_hash.hex())
    assert receipt["status"] == 1

    for op in generator:
        print("#" * 64, "BEGIN")
        if op == STEP_MINT:
            tx_to = np.random.choice(accounts, 1)[0]
            mint_value = int(np.random.choice(1000000000, 1)[0])
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
            print(f"opcode {op} : {tx_to}, {mint_value}")
            tx_hash = chains[0].instance.functions.mint(tx_to, mint_value).transact({"from": accounts[0]})
            chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(chains[0].w3, tx_hash)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
        elif op == STEP_ENTER:
            tx_to = np.random.choice(accounts, 1)[0]
            root_balance = chains[0].instance.functions.balances(tx_to).call()
            trie_key = chains[0].instance.functions.getBalanceTrieKey(tx_to).call()
            trie_value = int_to_bytes(np.random.choice(int(root_balance), 1)[0]) if root_balance > 0 else "0x" + "0"*32
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
            print(f"opcode {op} : {tx_to}, {trie_key.hex()}, {trie_value}")
            tx_hash = rootchain_instance.functions.startEnter(chains[0].token_address, trie_key.hex(), trie_value).transact({"from": tx_to})
            chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(chains[0].w3, tx_hash)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
        elif op == STEP_EXIT:
            tx_to = np.random.choice(accounts, 1)[0]
            child_balance = chains[1].instance.functions.balances(tx_to).call()
            trie_key = chains[0].instance.functions.getBalanceTrieKey(tx_to).call()
            trie_value = int_to_bytes(np.random.choice(int(child_balance), 1)[0]) if child_balance > 0 else "0x" + "0"*32
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
            print(f"opcode {op} : {tx_to}, {trie_key.hex()}, {trie_value}")
            tx_hash = rootchain_instance.functions.startExit(chains[0].token_address, trie_key.hex(), trie_value).transact({"from": accounts[1]})
            chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(chains[0].w3, tx_hash)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
        elif op == STEP_CHILD_DUMMY_TRANSACTION:
            tx_from = np.random.choice(accounts, 1)[0]
            tx_to = np.random.choice(accounts, 1)[0]
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_from)
            print(f"opcode {op} : {tx_from}, {tx_to}")
            tx_hash = chains[1].w3.eth.sendTransaction({"from": tx_from, "to": tx_to, "value": 0})
            chains[1].w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(chains[1].w3, tx_hash)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_from)
        elif op == STEP_ROOT_TRANSFER:
            tx_from = np.random.choice(accounts, 1)[0]
            tx_to = np.random.choice(accounts, 1)[0]
            root_balance = chains[0].instance.functions.balances(tx_from).call()
            tx_value = int(np.random.choice(int(root_balance), 1)[0]) if root_balance > 0 else 0
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_from)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
            print(f"opcode {op} : {tx_from}, {tx_to}, {tx_value}")
            tx_hash = chains[0].instance.functions.transfer(tx_to, tx_value).transact({"from": tx_from})
            chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(chains[0].w3, tx_hash)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_from)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
        elif op == STEP_CHILD_TRANSFER:
            tx_from = np.random.choice(accounts, 1)[0]
            tx_to = np.random.choice(accounts, 1)[0]
            child_balance = chains[1].instance.functions.balances(tx_from).call()
            tx_value = int(np.random.choice(int(child_balance), 1)[0]) if child_balance > 0 else 0
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_from)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
            print(f"opcode {op} : {tx_from}, {tx_to}, {tx_value}")
            tx_hash = chains[1].instance.functions.transfer(tx_to, tx_value).transact({"from": tx_from})
            chains[1].w3.eth.waitForTransactionReceipt(tx_hash.hex())
            check_transaction_status(chains[1].w3, tx_hash)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_from)
            print_balance([chains[0].w3, chains[1].w3], [chains[0].instance, chains[1].instance], tx_to)
        print("#" * 64, "END")
        time.sleep(10)

