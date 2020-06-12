#!/bin/bash
OPERATOR_KEY="bfaa65473b85b3c33b2f5ddb511f0f4ef8459213ada2920765aaac25b4fe38c5"
OPERATOR="0x5e3230019fed7ab462e3ac277e7709b9b2716b4f"

DATADIR=.pls.staking/operator1

ROOTCHAIN_IP=127.0.0.1

./geth \
    attach http://127.0.0.1:28545 \
    --datadir $DATADIR
