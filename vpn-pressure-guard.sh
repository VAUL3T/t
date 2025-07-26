#!/bin/bash

WG_INTERFACE="wg0"
MAX_RAM_USAGE=90
BLOCKED_CHAIN="WG_PRESSURE_BLOCK"

used_ram=$(free | awk '/Mem:/ { printf("%.0f", $3/$2 * 100) }')

chain_exists=$(iptables -L $BLOCKED_CHAIN 2>/dev/null)


if [ "$used_ram" -ge "$MAX_RAM_USAGE" ]; then
    echo "[!] RAM usage $used_ram% - blocking new connections..."

    if [ -z "$chain_exists" ]; then
        iptables -N $BLOCKED_CHAIN
        iptables -I INPUT -i $WG_INTERFACE -m conntrack --ctstate NEW -j $BLOCKED_CHAIN
        iptables -A $BLOCKED_CHAIN -j DROP
    fi
else
    echo "[+] RAM usage $used_ram% - allowing connections..."
    if [ ! -z "$chain_exists" ]; then
        iptables -D INPUT -i $WG_INTERFACE -m conntrack --ctstate NEW -j $BLOCKED_CHAIN
        iptables -F $BLOCKED_CHAIN
        iptables -X $BLOCKED_CHAIN
    fi
fi
