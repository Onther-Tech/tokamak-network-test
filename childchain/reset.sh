#!/bin/bash

rm -rf .pls.staking
mkdir -p .pls.staking/manager/keystore
cp ../keystore/* .pls.staking/manager/keystore

mkdir -p .pls.staking/operator1/keystore
cp ../keystore/* .pls.staking/operator1/keystore

./geth --nousb manage-staking deploy-managers 10 1.5 \
            --datadir ./.pls.staking/manager \
            --rootchain.url ws://127.0.0.1:8546 \
            --unlock 0xb79749F25Ef64F9AC277A4705887101D3311A0F4 \
            --password pwd.pass \
            --rootchain.sender 0xb79749F25Ef64F9AC277A4705887101D3311A0F4
            
./geth --nousb manage-staking deploy-powerton 60s \
            --datadir ./.pls.staking/manager \
            --rootchain.url ws://127.0.0.1:8546 \
            --unlock 0xb79749F25Ef64F9AC277A4705887101D3311A0F4 \
            --password pwd.pass \
            --rootchain.sender 0xb79749F25Ef64F9AC277A4705887101D3311A0F4
            
./geth --nousb manage-staking get-managers manager.json --datadir ./.pls.staking/manager

./geth --nousb manage-staking start-powerton \
            --datadir ./.pls.staking/manager \
            --rootchain.url ws://127.0.0.1:8546 \
            --unlock 0xb79749F25Ef64F9AC277A4705887101D3311A0F4 \
            --password pwd.pass \
            --rootchain.sender 0xb79749F25Ef64F9AC277A4705887101D3311A0F4
            
./deploy.operator1.sh

./geth --nousb init \
            --datadir .pls.staking/operator1 \
            --rootchain.url ws://localhost:8546 \
            genesis-operator1.json            
            
./geth --nousb \
            manage-staking set-managers manager.json  \
            --datadir ./.pls.staking/operator1
            
./geth --nousb \
            manage-staking get-managers \
            --datadir ./.pls.staking/operator1
            
./geth --nousb manage-staking register \
            --datadir ./.pls.staking/operator1 \
            --rootchain.url ws://127.0.0.1:8546 \
            --unlock 0x5e3230019fed7ab462e3ac277e7709b9b2716b4f \
            --password pwd.pass \
            --rootchain.sender 0x5e3230019fed7ab462e3ac277e7709b9b2716b4f

./geth \
    --nousb \
    --datadir ./.pls.staking/operator1 \
    --syncmode='full' \
    --networkid 102 \
    --rootchain.url ws://127.0.0.1:8546 \
    --operator 0x5e3230019fed7ab462e3ac277e7709b9b2716b4f \
    --rpc \
    --rpcaddr "0.0.0.0" \
    --rpcport 28545  \
    --rpcapi eth,net,personal,web3 \
    --port 30306 \
    --nat extip:::1 \
    --maxpeers 50 \
    --unlock 0x5e3230019fed7ab462e3ac277e7709b9b2716b4f \
    --password pwd.pass \
    --nodekeyhex e854e2f029be6364f0f961bd7571fd4431f99355b51ab79d23c56506f5f1a7c3 \
    --mine \
    --miner.gastarget 7500000 \
    --miner.gaslimit 10000000 \
    --allow-insecure-unlock \
    --verbosity 5

