#!/usr/bin/env bash
#
# A megszakadt apply/destroy után az Azure-ban létező erőforrásokat beolvassa
# a Terraform state-jébe. Csak azt importálja, ami hiányzik, tehát többször is
# futtatható. A `terraform import` nem hoz létre és nem módosít semmit: kizárólag
# a nyilvántartást (state) egészíti ki.
set -uo pipefail

SUB="$(awk -F'"' '/subscription_id/ {print $2}' terraform.tfvars)"
RG="szakdoga-rg"
BASE="/subscriptions/${SUB}/resourceGroups/${RG}"
NET="${BASE}/providers/Microsoft.Network"
NIC_ID="${NET}/networkInterfaces/szakdoga-nic"
NSG_ID="${NET}/networkSecurityGroups/szakdoga-nsg"

imports=(
  "azurerm_resource_group.main|${BASE}"
  "azurerm_virtual_network.main|${NET}/virtualNetworks/szakdoga-vnet"
  "azurerm_subnet.main|${NET}/virtualNetworks/szakdoga-vnet/subnets/szakdoga-subnet"
  "azurerm_network_security_group.main|${NSG_ID}"
  "azurerm_public_ip.main|${NET}/publicIPAddresses/szakdoga-ip"
  "azurerm_network_interface.main|${NIC_ID}"
  "azurerm_network_interface_security_group_association.main|${NIC_ID}|${NSG_ID}"
  "azurerm_linux_virtual_machine.main|${BASE}/providers/Microsoft.Compute/virtualMachines/szakdoga-vm"
)

state="$(terraform state list 2>/dev/null)"

for entry in "${imports[@]}"; do
  addr="${entry%%|*}"
  id="${entry#*|}"
  if grep -qxF "$addr" <<<"$state"; then
    printf '  már a state-ben: %s\n' "$addr"
    continue
  fi
  printf '\n→ import: %s\n' "$addr"
  terraform import "$addr" "$id" >/dev/null || {
    printf '  ELBUKOTT: %s\n' "$addr"
    continue
  }
  printf '  kész\n'
done

printf '\n=== a state tartalma ===\n'
terraform state list
