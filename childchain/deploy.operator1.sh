#!/bin/bash
OPERATOR_KEY="bfaa65473b85b3c33b2f5ddb511f0f4ef8459213ada2920765aaac25b4fe38c5"
OPERATOR="0x5e3230019fed7ab462e3ac277e7709b9b2716b4f"

DATADIR=.pls.staking/operator1

ROOTCHAIN_IP=127.0.0.1

# Deploy contracts at rootchain
echo "Deploy rootchain contract and others"
./geth \
    --nousb \
    --datadir $DATADIR \
    --rootchain.url "ws://$ROOTCHAIN_IP:8546" \
    --unlock $OPERATOR \
    --password pwd.pass \
    --rootchain.sender $OPERATOR \
    --rootchain.gasprice 20 \
    --stamina.operatoramount 1 \
    --stamina.mindeposit 0.5 \
    --stamina.recoverepochlength 120960 \
    --stamina.withdrawaldelay 362880 \
    deploy "./genesis-operator1.json" 102 true 2

# you can checkout "$geth deploy --help" for more information
