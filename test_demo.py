import pytest
import subprocess
import time
import os
import json
from web3 import Web3, HTTPProvider, IPCProvider
from web3.middleware import geth_poa_middleware

RUN_ROOTCHAIN_DIR = "rootchain"
RUN_CHILDCHAIN_DIR = "childchain"
RUN_ROOTCHAIN_PATH = "./run.rootchain.sh"
RUN_CHILDCHAIN_PATH = "./reset.sh"

def setup_chains():
    log_rootchain = open("log.rootchain", "w")
    log_childchain = open("log.childchain", "w")

    wd = os.getcwd()
    os.chdir(RUN_ROOTCHAIN_DIR)
    subprocess.Popen([RUN_ROOTCHAIN_PATH], stderr=log_rootchain)
    time.sleep(20)
    os.chdir(wd)
    os.chdir(RUN_CHILDCHAIN_DIR)
    child_chain = subprocess.Popen([RUN_CHILDCHAIN_PATH], stderr=log_childchain)
    os.chdir(wd)
    time.sleep(60)

setup_chains()
#time.sleep(60)

accounts = ["0xb79749F25Ef64F9AC277A4705887101D3311A0F4", "0x5E3230019fEd7aB462e3AC277E7709B9b2716b4F", "0x515B385bDc89bCc29077f2B00a88622883bfb498", "0xC927A0CF2d4a1B59775B5D0A35ec76d099e1FaD4", "0x48aFf0622a866d77651eAaA462Ea77b5F39D0ae1", "0xb715125A08140AEA83588a4b569599cde4a0a336", "0x499De281cd965781F1422b7cB73367C15DC416D2", "0xaA60af9BD19dc7438fd19457955C52982D070D27", "0x37da08b6Cd15c3aE905A25Df57B6841A5D80aC93", "0xec4A610a07e81264e8f7F1CAeAe522fEdD7e59c1"]

class ChainInfo:
    def __init__(self, ipc_path):
        self.ipc_path = ipc_path
        self.instance = None
        self.w3 = Web3(IPCProvider(ipc_path))

    def deploy_token(self):
        compiled_file = "RequestableSimpleToken.json"
        compiled_data = None
        with open(compiled_file) as f:
            compiled_data = json.load(f)

        instance = self.w3.eth.contract(abi= compiled_data['abi'], bytecode= compiled_data['bytecode'])
        tx_hash = instance.constructor().transact({'from': accounts[1]})

        print(f"deploy tx : {tx_hash.hex()}")

        self.w3.eth.waitForTransactionReceipt(tx_hash.hex())
        receipt = self.w3.eth.getTransactionReceipt(tx_hash.hex())
        print(f"contract address : {receipt['contractAddress']}")
        self.token_address = receipt["contractAddress"]
        self.instance = self.w3.eth.contract(abi= compiled_data['abi'], address=self.token_address)


def int_to_bytes(value):
    data = format(value, "x")
    return "0" * (64 - len(data)) + data

def print_step(chain_name, function_name, chains):
    print("#"*64, f"{chain_name} - {function_name}")
    root_block_number = chains[0].w3.eth.getBlock("latest").number
    child_block_number = chains[1].w3.eth.getBlock("latest").number
    print(f"# latest block number : {root_block_number}, {child_block_number}")
    time.sleep(10)

def test_demo():
    print("#"*64, "test demo")
    rootchain_ipc_path = "rootchain/root-chain-node-1/geth.ipc"
    operator_ipc_path = "childchain/.pls.staking/operator1/geth.ipc"
    rootchain_compiled_file = "RootChain.json"
    rootchain_addr = "0xC4BF071B54914221cC047F480293231E7DF9F85B"

    w3_rootchain = ChainInfo(rootchain_ipc_path)
    w3_childchain = ChainInfo(operator_ipc_path)

    rootchain_compiled_data = None
    with open(rootchain_compiled_file) as f:
        rootchain_compiled_data = json.load(f)
    rootchain_instance = w3_rootchain.w3.eth.contract(abi= rootchain_compiled_data['abi'], address=rootchain_addr)

    chains = [w3_rootchain, w3_childchain]
    for chain in chains:
        chain.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        chain.w3.geth.personal.unlock_account(accounts[1], "", 0)

        chain.deploy_token()
        print("#" * 64)

    # mint
    print_step("root", "mint", chains)
    tx_hash = chains[0].instance.functions.mint(accounts[1], chains[0].w3.toWei(5, "ether")).transact({"from": accounts[1]})
    print(f"mint tx : {tx_hash.hex()}")
    chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
    receipt = chains[0].w3.eth.getTransactionReceipt(tx_hash.hex())
    if receipt["status"] != 1:
        exit()

    # map
    print_step("root", "mapping", chains)
    tx_hash = rootchain_instance.functions.mapRequestableContractByOperator(chains[0].token_address, chains[1].token_address).transact({"from": accounts[1]})
    print(f"mapping address tx : {tx_hash.hex()}")
    chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
    receipt = chains[0].w3.eth.getTransactionReceipt(tx_hash.hex())
    if receipt["status"] != 1:
        exit()

    # enter
    print_step("root", "enter", chains)
    trie_key = chains[0].instance.functions.getBalanceTrieKey(accounts[1]).call()
    trie_value = int_to_bytes(chains[0].w3.toWei(1, "ether"))
    print(f"token address : {chains[0].token_address}")
    print(f"trie key : {trie_key.hex()}")
    print(f"trie value : {trie_value}")
    for i in range(5):
        tx_hash = rootchain_instance.functions.startEnter(chains[0].token_address, trie_key.hex(), trie_value).transact({"from": accounts[1]})
        print(f"startEnter tx : {tx_hash.hex()}")
        chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())

    # get NRE length
    print_step("root", "get NRE length", chains)
    nre_length = rootchain_instance.functions.NRELength().call()
    print(f"NRE length : {nre_length}")

    # make NRB for enter requests
    print_step("child", "make NRB for enter requests", chains)
    for i in range(nre_length * 2):
        tx_hash = chains[1].w3.eth.sendTransaction({"from": accounts[1], "to": accounts[1], "value": 0})
        print(f"tx : {tx_hash.hex()}")
        chains[1].w3.eth.waitForTransactionReceipt(tx_hash.hex())

    # exit
    print_step("root", "exit", chains)
    trie_key = chains[0].instance.functions.getBalanceTrieKey(accounts[1]).call()
    trie_value = int_to_bytes(chains[0].w3.toWei(1, "ether"))
    print(f"token address : {chains[0].token_address}")
    print(f"trie key : {trie_key.hex()}")
    print(f"trie value : {trie_value}")
    for i in range(5):
        tx_hash = rootchain_instance.functions.startExit(chains[0].token_address, trie_key.hex(), trie_value).transact({"from": accounts[1]})
        print(f"startExit tx : {tx_hash.hex()}")
        chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())

    # make NRB for exit requests
    print_step("child", "make NRB for exit requests", chains)
    for i in range(nre_length * 2):
        tx_hash = chains[1].w3.eth.sendTransaction({"from": accounts[1], "to": accounts[1], "value": 0})
        print(f"tx : {tx_hash.hex()}")
        chains[1].w3.eth.waitForTransactionReceipt(tx_hash.hex())

    # get block number
    print_step("child", "get block number", chains)
    block_number = chains[1].w3.eth.getBlock("latest").number
    print(f"block number : {block_number}")

    # finalize block
    print_step("root", "finalize block", chains)
    while True:
        try:
            tx_hash = rootchain_instance.functions.finalizeBlock().transact({"from": accounts[1], "gas": 100000000})
        except Exception as ex:
            break
        print(f"finalize tx : {tx_hash.hex()}")
        chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())
        receipt = chains[0].w3.eth.getTransactionReceipt(tx_hash.hex())
        if receipt["status"] == 0:
            break

    # finalize requests
    print_step("root", "finalize requests", chains)
    tx_hash = rootchain_instance.functions.finalizeRequests(10).transact({"from": accounts[1]})
    print(f"finalize tx : {tx_hash.hex()}")
    chains[0].w3.eth.waitForTransactionReceipt(tx_hash.hex())



test_demo()
