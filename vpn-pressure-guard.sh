#!/bin/bash

WG_INTERFACE="wg0"
MAX_RAM_USAGE=90
BLOCKED_CHAIN="WG_PRESSURE_BLOCK"

used_ram=$(free | awk '/Mem:/ { printf("%.0f", $3/$2 * 100) }')
timestamp=$(date "+%Y-%m-%d %H:%M:%S")

clients=$(wg show $WG_INTERFACE | grep "peer:" | awk '{print substr($2,1,6)}')
client_count=$(echo "$clients" | wc -l)

if [ "$client_count" -eq 0 ]; then
    client_list="none"
else
    client_list=$(echo "$clients" | tr '\n' ' ')
fi

echo "[$timestamp] [*] $client_count Device(s) connected [$client_list] | RAM Usage: ${used_ram}%"

chain_exists=$(iptables -L $BLOCKED_CHAIN 2>/dev/null)

if [ "$used_ram" -ge "$MAX_RAM_USAGE" ]; then
    echo "[$timestamp] [!] RAM usage high → Blocking new VPN connections..."

    if [ -z "$chain_exists" ]; then
        iptables -N $BLOCKED_CHAIN
        iptables -I INPUT -i $WG_INTERFACE -m conntrack --ctstate NEW -j $BLOCKED_CHAIN
        iptables -A $BLOCKED_CHAIN -j DROP
    fi
else
    echo "[$timestamp] [+] RAM normal → Allowing VPN connections."
    if [ ! -z "$chain_exists" ]; then
        iptables -D INPUT -i $WG_INTERFACE -m conntrack --ctstate NEW -j $BLOCKED_CHAIN
        iptables -F $BLOCKED_CHAIN
        iptables -X $BLOCKED_CHAIN
    fi
fi
